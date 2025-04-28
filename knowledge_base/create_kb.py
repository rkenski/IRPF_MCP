from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, QueryBundle, StorageContext
from llama_index.core.readers.json import JSONReader
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever
from llama_index.core.schema import NodeWithScore
from llama_index.core.node_parser import SentenceSplitter
from llama_cloud_services import LlamaParse
from typing import List
import Stemmer
import nest_asyncio
nest_asyncio.apply()

PERSIST_FOLDER = "faiss"

parser = LlamaParse(
    num_workers=3,
    do_not_cache=True)

file_extractor = {".pdf": parser,
                    ".json": JSONReader(),
                    ".txt": parser,
                    ".doc": parser,
                    ".docx": parser}

# Load documents
documents = SimpleDirectoryReader(input_dir="dados",
                                 required_exts=[".pdf", ".json", ".txt", ".doc", ".docx"],
                                 file_extractor=file_extractor).load_data()

# Function to create retrievers
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

# Main processing
node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=200)

nodes = node_parser.get_nodes_from_documents(documents, show_progress=True)

#### Creating Retrievers
similarity_top_k = 4

embedding_retriever = create_embedding_retriever(
    nodes, similarity_top_k=similarity_top_k
)
bm25_retriever = create_bm25_retriever(
    nodes, similarity_top_k=similarity_top_k
)
embedding_bm25_retriever_rerank = EmbeddingBM25RerankerRetriever(
    embedding_retriever, bm25_retriever
)

# set up ChromaVectorStore and load in data
# create client and a new collection
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding

db = chromadb.PersistentClient(path="chroma_db")
chroma_collection = db.get_or_create_collection("IRPF")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
embed_model = OpenAIEmbedding(model="text-embedding-3-large")

index = VectorStoreIndex.from_documents(
    documents, storage_context=storage_context, embed_model=embed_model
)

# load from disk
db2 = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = db2.get_or_create_collection("IRPF")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
index = VectorStoreIndex.from_vector_store(
    vector_store,
    embed_model=embed_model,
)


query_engine = index.as_query_engine()
response = query_engine.query("Qual é a data limite para entrega da declaração?")
print(response)






