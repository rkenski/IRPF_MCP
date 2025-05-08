from mcp.server.fastmcp import FastMCP
from pathlib import Path
import yaml
import json
import logging
import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
import time
from xml2Pydantic import parse_irpf2025

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IRPF_MCP")

# Create MCP server
mcp = FastMCP("IRPF_MCP")
config = {}

# Global variables for ChromaDB
chroma_client = None
chroma_collection = None
vector_store = None
index = None
query_engine = None
embed_model = None

# Load configuration
def load_config():
    try:
        with open("setup.yaml", "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {"IRPF_DIR_2025": "irpf/2025", "CPF": "00000000000", "DB_DIR": "./database"}

# Initialize ChromaDB client
def initialize_chroma_client():
    global chroma_client, chroma_collection, vector_store, index, query_engine, embed_model
    
    try:
        # Initialize embedding model if not already done
        if embed_model is None:
            embed_model = OpenAIEmbedding(model="text-embedding-3-large")
            
        # Connect to existing ChromaDB
        chroma_client = chromadb.PersistentClient(path="knowledge_base/chroma_db")
        chroma_collection = chroma_client.get_or_create_collection("IRPF")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=embed_model,
        )
        query_engine = index.as_query_engine()
        logger.info("ChromaDB client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing ChromaDB client: {e}")
        # Set to None so we can check if initialization failed
        chroma_client = None
        query_engine = None

# Resource function for reading tax return
@mcp.tool()
def read_tax_return():
    """
    Reads the current tax return XML file.

    Returns:
        str: JSON representation of the tax return
    """
    try:
        ir_xml = Path.home() / config['IRPF_DIR_2025'] / "aplicacao" / "dados" / str(config['CPF']) / f"{config['CPF']}-0000000000.xml"
        logger.info(f"Reading tax return from {ir_xml}")
        
        if not ir_xml.exists():
            logger.error(f"Tax return file not found: {ir_xml}")
            return json.dumps({"error": "Tax return file not found"}, indent=2, ensure_ascii=False)
        
        decl = parse_irpf2025(ir_xml)
        return json.dumps(decl.model_dump(mode="json"), indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error reading tax return: {e}")
        return json.dumps({"error": f"Failed to read tax return: {str(e)}"}, indent=2, ensure_ascii=False)

# Tool function for checking tax return status
@mcp.tool()
def check_tax_return_status():
    """
    Checks if the tax return is available and accessible.
    
    Returns:
        dict: Status of the tax return with basic information.
    """
    logger.info("Verificando status da declaração")
    try:
        # Try to access the XML file
        ir_xml = Path.home() / config['IRPF_DIR_2025'] / "aplicacao" / "dados" / str(config['CPF']) / f"{config['CPF']}-0000000000.xml"
        
        if ir_xml.exists():
            file_size = ir_xml.stat().st_size
            file_modified = ir_xml.stat().st_mtime
            
            return {
                "status": "disponível",
                "arquivo": str(ir_xml),
                "tamanho": f"{file_size / 1024:.2f} KB",
                "ultima_modificacao": file_modified,
                "mensagem": "A declaração está disponível para acesso"
            }
        else:
            return {
                "status": "indisponível",
                "arquivo": str(ir_xml),
                "mensagem": "O arquivo da declaração não foi encontrado"
            }
    except Exception as e:
        logger.error(f"Erro ao verificar status: {e}")
        return {
            "status": "erro",
            "mensagem": f"Erro ao verificar o status da declaração: {str(e)}"
        }

# Tool function for querying the knowledge base
@mcp.tool()
def query_kb(query: str):
    """
    Query the IRPF knowledge base.
    
    Args:
        query (str): The query to search in the knowledge base
        
    Returns:
        str: Response from the knowledge base
    """
    global query_engine
    
    try:
        logger.info(f"Querying knowledge base: {query}")
        
        # Check if we need to initialize the ChromaDB client
        if query_engine is None:
            logger.info("Query engine not initialized, attempting to initialize...")
            initialize_chroma_client()
            if query_engine is None:
                return "Error: Unable to initialize knowledge base query engine"
        
        # Use the pre-initialized query engine
        response = query_engine.query(query)
        return str(response)
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        
        # Try to reinitialize if there was an error
        try:
            logger.info("Attempting to reinitialize ChromaDB client after error...")
            # Clean up existing client if it exists
            if chroma_client is not None:
                try:
                    chroma_client.close()
                except:
                    pass
            
            # Reinitialize
            time.sleep(1)  # Brief pause before reconnecting
            initialize_chroma_client()
            
            if query_engine is not None:
                logger.info("Successfully reinitialized ChromaDB client")
                response = query_engine.query(query)
                return str(response)
        except Exception as reinit_error:
            logger.error(f"Error reinitializing ChromaDB client: {reinit_error}")
        
        return f"Error querying knowledge base: {str(e)}"

if __name__ == "__main__":
    print("🚀 Starting IRPF MCP server...")
    config = load_config()

    # Run the server
    mcp.run("stdio")
