#!/usr/bin/env python3
"""
IRPF MCP Setup Script

This script performs all the initialization tasks needed before running server_minimal.py:
1. Creates and updates the knowledge base
2. Processes new personal documents
3. Initializes database connections
4. Ensures all necessary directories exist

Run this script during initial setup or whenever there are new files in the input folders,
before starting the server_minimal.py.
"""

import logging
import sys
import yaml
import time
from pathlib import Path
import duckdb
import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("irpf_mcp_setup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IRPF_MCP_Setup")

def load_config(config_path: str = "setup.yaml"):
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dict containing configuration values
    """
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        # Create a default configuration if file doesn't exist
        default_config = {
            "IRPF_DIR_2025": "irpf/2025",
            "CPF": "00000000000",
            "DB_DIR": "./database"
        }
        
        # Write default config to file
        try:
            with open(config_path, "w", encoding="utf-8") as file:
                yaml.dump(default_config, file)
            logger.info(f"Created default configuration at {config_path}")
        except Exception as write_error:
            logger.error(f"Error creating default configuration: {write_error}")
            
        return default_config

def initialize_knowledge_base():
    """
    Initialize the knowledge base by creating the chroma_db if it doesn't exist.
    """
    try:
        from knowledge_base.create_kb import create_knowledge_base
        
        kb_path = Path("knowledge_base/chroma_db")
        if not kb_path.exists() or not any(kb_path.iterdir()):
            logger.info("Knowledge base not found or empty. Creating new knowledge base...")
            create_knowledge_base()
            logger.info("Knowledge base created successfully")
        else:
            logger.info(f"Knowledge base found at {kb_path}")
    except Exception as e:
        logger.error(f"Error initializing knowledge base: {e}")
        # Create a minimal knowledge base structure if the import fails
        kb_path = Path("knowledge_base/chroma_db")
        kb_path.mkdir(parents=True, exist_ok=True)
        logger.info("Created minimal knowledge base structure")

def process_personal_documents():
    """
    Check for new documents in meus_arquivos/originais and process them if needed.
    """
    try:
        from meus_arquivos.db_arquivos_pessoais import process_personal_documents
        
        logger.info("Checking for personal documents...")
        # Get the absolute path to the meus_arquivos directory
        meus_arquivos_path = Path(__file__).parent / "meus_arquivos"
        processed = process_personal_documents(source_folder=meus_arquivos_path)
        
        if processed:
            logger.info("Personal documents processed successfully")
        else:
            logger.info("No new personal documents to process")
            
    except Exception as e:
        logger.error(f"Error processing personal documents: {e}")
        # Create the necessary directories if they don't exist
        originais_dir = Path(__file__).parent / "meus_arquivos/originais"
        data_files_dir = Path(__file__).parent / "meus_arquivos/data_files"
        originais_dir.mkdir(parents=True, exist_ok=True)
        data_files_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directories {originais_dir} and {data_files_dir}")

def initialize_db_connection(config):
    """
    Initialize the DuckDB database connection and create tables if needed.
    
    Args:
        config: Configuration dictionary
    """
    try:
        db_dir = Path(config.get('DB_DIR', './database'))
        duck_db_path = db_dir / "irpf_database.duckdb"
        
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created database directory at {db_dir}")
        
        conn = duckdb.connect(str(duck_db_path))
        logger.info(f"Connected to DuckDB at {duck_db_path}")
        
        # Check if tables exist and create them if needed
        try:
            # Check if the declarations table exists
            result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='declarations'").fetchall()
            if not result:
                logger.info("Creating database tables...")
                # Create tables (simplified schema)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS declarations (
                    declaration_id INTEGER PRIMARY KEY,
                    file_name TEXT,
                    cpf TEXT,
                    year INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                conn.execute("""
                CREATE TABLE IF NOT EXISTS rendimentos_tributaveis_pj (
                    id INTEGER PRIMARY KEY,
                    declaration_id INTEGER,
                    nome_fonte_pagadora TEXT,
                    cnpj_fonte TEXT,
                    rendimentos DECIMAL(15,2),
                    FOREIGN KEY (declaration_id) REFERENCES declarations(declaration_id)
                )
                """)
                
                conn.execute("""
                CREATE TABLE IF NOT EXISTS rendimentos_exclusivos (
                    id INTEGER PRIMARY KEY,
                    declaration_id INTEGER,
                    nome_fonte_pagadora TEXT,
                    cnpj_fonte TEXT,
                    valor DECIMAL(15,2),
                    FOREIGN KEY (declaration_id) REFERENCES declarations(declaration_id)
                )
                """)
                
                conn.execute("""
                CREATE TABLE IF NOT EXISTS rendimentos_isentos (
                    id INTEGER PRIMARY KEY,
                    declaration_id INTEGER,
                    nome_fonte_pagadora TEXT,
                    cnpj_fonte TEXT,
                    valor DECIMAL(15,2),
                    FOREIGN KEY (declaration_id) REFERENCES declarations(declaration_id)
                )
                """)
                
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pagamentos_efetuados (
                    id INTEGER PRIMARY KEY,
                    declaration_id INTEGER,
                    codigo TEXT,
                    nome_beneficiario TEXT,
                    cpf_cnpj_beneficiario TEXT,
                    valor_pago DECIMAL(15,2),
                    FOREIGN KEY (declaration_id) REFERENCES declarations(declaration_id)
                )
                """)
                
                conn.execute("""
                CREATE TABLE IF NOT EXISTS bens_direitos (
                    id INTEGER PRIMARY KEY,
                    declaration_id INTEGER,
                    codigo TEXT,
                    grupo TEXT,
                    descricao TEXT,
                    valor_2023 DECIMAL(15,2),
                    valor_2024 DECIMAL(15,2),
                    FOREIGN KEY (declaration_id) REFERENCES declarations(declaration_id)
                )
                """)
                
                logger.info("Database tables created successfully")
        except Exception as table_error:
            logger.error(f"Error creating database tables: {table_error}")
        
        conn.close()
        logger.info("Database connection closed")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def initialize_chroma_client():
    """
    Initialize the ChromaDB client to verify it's working correctly.
    """
    try:
        # Initialize embedding model
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
        
        logger.info("ChromaDB client initialized and verified successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing ChromaDB client: {e}")
        return False

def add_to_python_path():
    """
    Add the project root to the Python path to enable imports.
    """
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
        logger.info(f"Added {project_root} to Python path")

def main():
    """
    Main function to run all setup tasks.
    """
    print("🚀 Starting IRPF MCP Setup...")
    
    # Add to Python path
    add_to_python_path()
    
    # Load configuration
    config = load_config()
    
    # Initialize knowledge base
    initialize_knowledge_base()
    
    # Process personal documents
    process_personal_documents()
    
    # Initialize database
    db_initialized = initialize_db_connection(config)
    
    # Verify ChromaDB client
    chroma_initialized = initialize_chroma_client()
    
    # Final status
    if db_initialized and chroma_initialized:
        print("✅ Setup completed successfully! You can now run server.py")
    else:
        print("⚠️ Setup completed with warnings. Check the logs for details.")
        if not db_initialized:
            print("   - Database initialization had issues")
        if not chroma_initialized:
            print("   - ChromaDB initialization had issues")

if __name__ == "__main__":
    main()
