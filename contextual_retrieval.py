import os
import logging
import nest_asyncio
import Stemmer
import faiss
from typing import List, Dict

from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core import (
    SimpleDirectoryReader, Settings, VectorStoreIndex, 
    QueryBundle, StorageContext, Document
)
from llama_index.postprocessor.voyageai_rerank import VoyageAIRerank
from llama_index.embeddings.voyageai import VoyageEmbedding
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever
from llama_index.core.schema import NodeWithScore
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import DocxReader
from pathlib import Path

# Configuration
PERSIST_FOLDER = "contract_index"
SIMILARITY_TOP_K = 20
CHUNK_SIZE = 1024  # tokens
CHUNK_OVERLAP = 200  # tokens

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Apply nest_asyncio for running nested asyncio loops
nest_asyncio.apply()

def setup_environment():
    voyage_api_key = os.getenv("VOYAGE_API_KEY")
    if not voyage_api_key:
        logger.error("VOYAGE_API_KEY not found in environment variables.")
        raise EnvironmentError("VOYAGE_API_KEY must be set in environment variables.")
    
    Settings.embed_model = VoyageEmbedding(voyage_api_key=voyage_api_key, model_name="voyage-law-2")
    return voyage_api_key

def get_pdf_parser() -> PDFReader:
    """
    Returns a PDFReader instance configured for full document return.
    """
    return PDFReader(return_full_document=True)

def process_file(file_path: str) -> Document:
    """
    Process a single document file and return a Document object.
    """
    file_path = Path(file_path)
    file_extension = file_path.suffix.lower()
    
    if file_extension == '.pdf':
        parser = get_pdf_parser()
    elif file_extension == '.docx':
        parser = DocxReader()
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")
    
    try:
        if file_extension == '.pdf':
            document = parser.load_data(file=file_path)
        else:  # .docx
            document = parser.load_data(file=file_path)
        
        if document:
            logger.info(f"Processed document: {file_path}")
            return document
        else:
            raise ValueError(f"No content found in document: {file_path}")
    except Exception as e:
        logger.error(f"Error processing document {file_path}: {e}")
        raise


def ingest_documents(data_folder: str) -> List[Document]:
    """
    Ingest documents from a specified folder.
    """
    file_extractor: Dict[str, PDFReader] = {".pdf": get_pdf_parser()}

    try:
        documents = SimpleDirectoryReader(
            input_dir=data_folder,
            required_exts=[".pdf", ".PDF"],
            recursive=True,
            file_extractor=file_extractor
        ).load_data()
        logger.info(f"Loaded {len(documents)} documents from {data_folder}.")
        return documents
    except Exception as e:
        logger.error(f"Error loading documents: {e}")
        raise

def create_embedding_retriever(nodes: List, similarity_top_k: int = 2) -> VectorIndexRetriever:
    vector_index = VectorStoreIndex(nodes)
    return vector_index.as_retriever(similarity_top_k=similarity_top_k)

def create_bm25_retriever(nodes: List, similarity_top_k: int = 2) -> BM25Retriever:
    return BM25Retriever.from_defaults(
        nodes=nodes, 
        similarity_top_k=similarity_top_k, 
        stemmer=Stemmer.Stemmer("english"), 
        language="english"
    )

def set_node_ids(nodes: List) -> List:
    for index, node in enumerate(nodes):
        node.id_ = f"node_{index}"
    return nodes

class EmbeddingBM25RerankerRetriever(BaseRetriever):
    def __init__(
        self,
        vector_retriever: VectorIndexRetriever,
        bm25_retriever: BM25Retriever,
        reranker: VoyageAIRerank,
    ) -> None:
        super().__init__()
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.reranker = reranker

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        vector_nodes = self.vector_retriever.retrieve(query_bundle)
        bm25_nodes = self.bm25_retriever.retrieve(query_bundle)
        combined_nodes = vector_nodes + bm25_nodes
        return self.reranker.postprocess_nodes(combined_nodes, query_bundle)

def create_vector_index(documents: List[Document], persist_folder: str = PERSIST_FOLDER) -> VectorStoreIndex:
    """
    Create a vector index from a list of documents.
    """
    voyage_api_key = setup_environment()

    node_parser = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    nodes = node_parser.get_nodes_from_documents(documents, show_progress=True)
    nodes = set_node_ids(nodes)

    voyageai_rerank = VoyageAIRerank(
        api_key=voyage_api_key, 
        top_n=SIMILARITY_TOP_K, 
        model="rerank-2", 
        truncation=True
    )

    embedding_retriever = create_embedding_retriever(nodes, similarity_top_k=SIMILARITY_TOP_K)
    bm25_retriever = create_bm25_retriever(nodes, similarity_top_k=SIMILARITY_TOP_K)

    embedding_bm25_retriever_rerank = EmbeddingBM25RerankerRetriever(
        embedding_retriever, 
        bm25_retriever, 
        reranker=voyageai_rerank
    )

    try:
        if os.path.exists(persist_folder):
            vector_index = VectorStoreIndex.load(persist_dir=persist_folder)
            logger.info(f"Loaded existing vector index from {persist_folder}.")
        else:
            d = CHUNK_SIZE
            faiss_index = faiss.IndexFlatL2(d)
            os.makedirs(persist_folder, exist_ok=True)

            vector_store = FaissVectorStore(faiss_index=faiss_index)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            vector_index = VectorStoreIndex(
                nodes, 
                retriever=embedding_bm25_retriever_rerank, 
                storage_context=storage_context
            )
            vector_index.storage_context.persist(persist_dir=persist_folder)
            logger.info(f"Vector index created and persisted at {persist_folder}.")
        
        return vector_index
    except Exception as e:
        logger.error(f"Error during vector index creation or persistence: {e}")
        raise

# Example usage:
# documents = ingest_documents("path/to/your/data/folder")
# vector_index = create_vector_index(documents)