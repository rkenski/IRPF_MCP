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
import duckdb
import pandas as pd
from xml2Pydantic import parse_irpf2025

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IRPF_MCP")

# Create MCP server
mcp = FastMCP("IRPF_MCP")

# Load configuration immediately
def load_config():
    try:
        with open("setup.yaml", "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {"IRPF_DIR_2025": "irpf/2025", "CPF": "00000000000", "DB_DIR": "./database"}

# Load configuration immediately
config = load_config()
logger.info(f"Configuration loaded: IRPF_DIR={config.get('IRPF_DIR_2025')}, CPF={config.get('CPF')}")

# Global variables for ChromaDB
chroma_client = None
chroma_collection = None
vector_store = None
index = None
query_engine = None
embed_model = None

# Global variables for DuckDB
duck_conn = None

# Initialize connections immediately

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

# Initialize DuckDB connection
def initialize_db_connection():
    global duck_conn, config
    
    try:
        logger.info(f"Initializing DB connection with config: {config}")
        db_dir = Path(config.get('DB_DIR', './database'))
        duck_db_path = db_dir / "irpf_database.duckdb"
        
        logger.info(f"Checking if database path exists: {duck_db_path}")
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created database directory at {db_dir}")
        
        if not duck_db_path.exists():
            logger.warning(f"Database file does not exist at {duck_db_path}")
        else:
            logger.info(f"Database file exists at {duck_db_path}, size: {duck_db_path.stat().st_size} bytes")
        
        logger.info(f"Connecting to DuckDB at {duck_db_path}")
        conn = duckdb.connect(str(duck_db_path))
        logger.info(f"Connected to DuckDB at {duck_db_path}")
        
        # Test the connection
        test_result = conn.execute("SELECT 1 as test").fetchdf()
        logger.info(f"Connection test result: {test_result}")
        
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        logger.exception("Detailed exception information:")
        return None

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

# Tool function for querying the database
@mcp.tool()
def query_irpf_db(sql_query: str):
    """
    Execute a SQL query against the IRPF DuckDB database.
    
    Args:
        sql_query (str): SQL query to execute
        
    Returns:
        pandas.DataFrame: Result of the query
    """
    global duck_conn, config
    
    logger.info(f"query_irpf_db called with query: {sql_query[:50]}...")
    logger.info(f"Current config: {config}")
    logger.info(f"Current duck_conn: {duck_conn}")
    
    try:
        # Check if we need to initialize the DuckDB connection
        if duck_conn is None:
            logger.info("DuckDB connection is None, initializing...")
            duck_conn = initialize_db_connection()
            logger.info(f"After initialization, duck_conn: {duck_conn}")
            if duck_conn is None:
                logger.error("Failed to initialize DuckDB connection")
                return pd.DataFrame()
        
        logger.info(f"Executing SQL query using connection: {duck_conn}")
        result = duck_conn.execute(sql_query).fetchdf()
        logger.info(f"Query result shape: {result.shape}")
        return result
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        logger.exception("Detailed exception information:")
        return pd.DataFrame()

# Tool function for finding salary income
@mcp.tool()
def find_salary_income():
    """
    Find all salary income records in the database.
    
    Returns:
        pandas.DataFrame: Salary income records
    """
    query = """
    SELECT d.file_name, r.nome_fonte_pagadora, r.rendimentos
    FROM rendimentos_tributaveis_pj r
    JOIN declarations d ON r.declaration_id = d.declaration_id
    ORDER BY r.rendimentos DESC
    """
    logger.info("Finding salary income")
    return query_irpf_db(query)

# Tool function for calculating total payments by category
@mcp.tool()
def total_payments_by_category():
    """
    Calculate total payments by category.
    
    Returns:
        pandas.DataFrame: Total payments grouped by category
    """
    query = """
    SELECT codigo, SUM(valor_pago) as total_value
    FROM pagamentos_efetuados
    GROUP BY codigo
    ORDER BY total_value DESC
    """
    logger.info("Calculating total payments by category")
    return query_irpf_db(query)

# Tool function for analyzing assets
@mcp.tool()
def analyze_assets():
    """
    Analyze assets with detailed statistics.
    
    Returns:
        pandas.DataFrame: Asset analysis results
    """
    query = """
    SELECT 
        grupo, 
        COUNT(*) as count,
        SUM(valor_2024) as total_value_2024,
        AVG(valor_2024) as avg_value_2024,
        MIN(valor_2024) as min_value_2024,
        MAX(valor_2024) as max_value_2024
    FROM bens_direitos
    GROUP BY grupo
    ORDER BY total_value_2024 DESC
    """
    logger.info("Analyzing assets")
    return query_irpf_db(query)

# Tool function for finding all income sources
@mcp.tool()
def all_income_sources():
    """
    Find all income sources across different categories.
    
    Returns:
        pandas.DataFrame: All income sources
    """
    logger.info("all_income_sources called")
    
    # First check if tables exist
    check_query = """SELECT table_name FROM information_schema.tables 
                   WHERE table_schema='main' AND 
                   table_name IN ('rendimentos_tributaveis_pj', 'rendimentos_exclusivos', 'rendimentos_isentos');"""
    
    logger.info("Checking if tables exist...")
    tables_df = query_irpf_db(check_query)
    logger.info(f"Tables found: {tables_df}")
    
    if tables_df.empty:
        logger.warning("No tables found in database")
        # Try to list all tables
        all_tables = query_irpf_db("SELECT table_name FROM information_schema.tables WHERE table_schema='main'")
        logger.info(f"All tables in database: {all_tables}")
        return pd.DataFrame({'mensagem': ['Nenhuma tabela de receitas encontrada no banco de dados']})
    
    query = """
    WITH 
    tributaveis AS (
        SELECT 
            'Tributável PJ' as tipo, 
            nome_fonte_pagadora as fonte, 
            rendimentos as valor 
        FROM rendimentos_tributaveis_pj
    ),
    exclusivos AS (
        SELECT 
            'Exclusivo' as tipo, 
            nome_fonte_pagadora as fonte, 
            valor 
        FROM rendimentos_exclusivos
    ),
    isentos AS (
        SELECT 
            'Isento' as tipo, 
            nome_fonte_pagadora as fonte, 
            valor 
        FROM rendimentos_isentos
        WHERE nome_fonte_pagadora IS NOT NULL
    )
    
    SELECT * FROM tributaveis
    UNION ALL 
    SELECT * FROM exclusivos
    UNION ALL 
    SELECT * FROM isentos
    ORDER BY valor DESC
    """
    logger.info("Executing income sources query")
    result = query_irpf_db(query)
    logger.info(f"Income sources query result: {result}")
    return result

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

# Initialize connections
initialize_chroma_client()
duck_conn = initialize_db_connection()

if __name__ == "__main__":
    print("🚀 Starting IRPF MCP server...")
    
    # Run the server
    mcp.run("stdio")
