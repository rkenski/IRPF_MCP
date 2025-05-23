from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, QueryBundle, StorageContext
from llama_index.core.readers.json import JSONReader
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever
from llama_index.core.schema import NodeWithScore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.docling import DoclingReader
from llama_index.readers.file import PDFReader
from typing import List
import Stemmer
import nest_asyncio
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
import json
from pathlib import Path
from datetime import datetime

nest_asyncio.apply()

def create_knowledge_base(input_dir=None, collection_name="IRPF", db_path="chroma_db", force_processing=False):
    """
    Create a knowledge base from documents in the specified input directory.
    Only processes files if they aren't already included in the Chroma database.
    
    Args:
        input_dir (str): Directory containing documents to process
        collection_name (str): Name of the collection in ChromaDB
        db_path (str): Path to store the ChromaDB database
        force_processing (bool): Force processing even if no new files are detected
        
    Returns:
        VectorStoreIndex: The created index
        bool: Whether processing was performed
    """
    # Determine project root as two levels up from this file
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent

    # Set input_dir to <project_root>/knowledge_base/dados if not specified
    if input_dir is None:
        input_dir = project_root / "knowledge_base" / "dados"
    else:
        input_dir = Path(input_dir)
        if not input_dir.is_absolute():
            input_dir = project_root / input_dir

    # Resolve db_path relative to project root if not absolute

    if not Path(db_path).is_absolute():
        db_path = project_root / "knowledge_base" / db_path

    # Ensure input_dir exists
    if not input_dir.exists():
        input_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created input directory at {input_dir}")
        
    # Create a marker file path to track processed files
    marker_dir = project_root / "knowledge_base" / "processed"
    marker_dir.mkdir(parents=True, exist_ok=True)
    processed_marker = marker_dir / f"{collection_name}_processed.json"
    
    # Check if there are documents to process
    document_files = []
    for ext in [".pdf", ".json", ".txt", ".doc", ".docx"]:
        document_files.extend(list(input_dir.glob(f"**/*{ext}")))
    
    if not document_files:
        print(f"No documents found in {input_dir}. Creating empty knowledge base.")
        # Create an empty ChromaDB collection
        db = chromadb.PersistentClient(path=str(db_path))
        chroma_collection = db.get_or_create_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        embed_model = OpenAIEmbedding(model="text-embedding-3-large")
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=embed_model,
        )
        return index, False
    
    # Check if processing is needed
    processing_needed = force_processing
    
    if not processed_marker.exists():
        print("No processed documents marker found. Processing needed.")
        processing_needed = True
    elif document_files:
        # Check if there are new files or modified files
        processed_time = processed_marker.stat().st_mtime
        processed_files = []
        
        if processed_marker.exists():
            try:
                with open(processed_marker, "r") as f:
                    processed_data = json.load(f)
                    processed_files = processed_data.get("processed_files", [])
            except (json.JSONDecodeError, FileNotFoundError):
                processing_needed = True
        
        # Check for new files or modified files
        for file_path in document_files:
            file_str = str(file_path.resolve())
            if file_str not in processed_files or file_path.stat().st_mtime > processed_time:
                print(f"New or modified file detected: {file_path}")
                processing_needed = True
                break
    
    if not processing_needed:
        print("All documents have already been processed")
        # Return existing index
        db = chromadb.PersistentClient(path=str(db_path))
        chroma_collection = db.get_or_create_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        embed_model = OpenAIEmbedding(model="text-embedding-3-large")
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=embed_model,
        )
        return index, False
        
    # Load documents if they exist
    try:
        documents = SimpleDirectoryReader(
            input_dir=input_dir,
            file_extractor= {".json": JSONReader()}
        ).load_data()

        # Process documents
        node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=200)
        nodes = node_parser.get_nodes_from_documents(documents, show_progress=True)
        
        # Set up ChromaVectorStore and load in data
        db = chromadb.PersistentClient(path=str(db_path))
        chroma_collection = db.get_or_create_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        embed_model = OpenAIEmbedding(model="text-embedding-3-large")
        
        # Create index
        index = VectorStoreIndex(
            nodes,
            storage_context=storage_context,
            embed_model=embed_model
        )
        
        # Update the processed marker file with the list of processed files
        processed_data = {
            "last_processed": datetime.now().isoformat(),
            "processed_files": [str(file_path.resolve()) for file_path in document_files]
        }
        
        with open(processed_marker, "w") as f:
            json.dump(processed_data, f, indent=4)
        
        print(f"Knowledge base created successfully with {len(documents)} documents")
        return index, True
    except Exception as e:
        print(f"Error creating knowledge base: {e}")
        # Create an empty ChromaDB collection on error
        db = chromadb.PersistentClient(path=db_path)
        chroma_collection = db.get_or_create_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        embed_model = OpenAIEmbedding(model="text-embedding-3-large")
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=embed_model,
        )
        return index, False

# Helper functions for retrievers
def create_embedding_retriever(nodes_, similarity_top_k=2):
    """Function to create an embedding retriever for a list of nodes."""
    vector_index = VectorStoreIndex(nodes_)
    retriever = vector_index.as_retriever(similarity_top_k=similarity_top_k)
    return retriever

def create_bm25_retriever(nodes_, similarity_top_k=2):
    """Function to create a bm25 retriever for a list of nodes."""
    bm25_retriever = BM25Retriever.from_defaults(
        nodes=nodes_, similarity_top_k=similarity_top_k, stemmer=Stemmer.Stemmer("english"), language="english"
    )
    return bm25_retriever

class EmbeddingBM25RerankerRetriever(BaseRetriever):
    """Custom retriever that uses both embedding and bm25 retrievers and reranker"""

    def __init__(
        self,
        vector_retriever: VectorIndexRetriever,
        bm25_retriever: BM25Retriever,
    ) -> None:
        """Init params."""

        self._vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever

        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Retrieve nodes given query."""

        vector_nodes = self._vector_retriever.retrieve(query_bundle)
        bm25_nodes = self.bm25_retriever.retrieve(query_bundle)

        vector_nodes.extend(bm25_nodes)

        return vector_nodes

# Run the knowledge base creation if this file is executed directly
if __name__ == "__main__":
    index, processed = create_knowledge_base()
    
    if processed:
        print("Knowledge base was updated with new documents.")
    else:
        print("No new documents to process.")
    
    # Test query
    query_engine = index.as_query_engine()
    response = query_engine.query("Qual é a data limite para entrega da declaração?")
    print(response)
