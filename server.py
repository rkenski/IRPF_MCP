from mcp.server.fastmcp import FastMCP
from chromadb import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from pathlib import Path
import yaml
from xml2Pydantic import parse_irpf2025
import json
import logging
import os
import duckdb
import pandas as pd
import argparse
from typing import Dict, Any, Optional
import shutil
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("irpf_mcp.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IRPF_MCP")

class IRPFMCPServer:
    """
    IRPF MCP Server for handling tax return data and queries.
    This server provides tools for:
    1. Reading and parsing tax declaration XML files
    2. Querying a database of personal financial documents
    3. Accessing a knowledge base of tax information
    """
    
    def __init__(self, config_path: str = "setup.yaml"):
        """
        Initialize the IRPF MCP Server.
        
        Args:
            config_path: Path to the configuration YAML file
        """
        self.mcp = FastMCP("IRPF_MCP")
        self.config = self._load_config(config_path)
        self.embed_model = OpenAIEmbedding(model="text-embedding-3-large")
        
        # Initialize database connection
        self.db_dir = Path(self.config.get('DB_DIR', './database'))
        self.duck_db_path = self.db_dir / "irpf_database.duckdb"
        self.duck_conn = self._initialize_db_connection()
        
        # Initialize knowledge base and process new documents
        self._initialize_system()
        
        # Register resources and tools
        self._register_resources()
        self._register_tools()
        
        logger.info("IRPF MCP Server initialized successfully")
    
    def _initialize_system(self):
        """
        Initialize the system by:
        1. Creating the knowledge base if it doesn't exist
        2. Processing new documents in meus_arquivos/originais if there are any
        """
        logger.info("Initializing system...")
        
        # Add the project root to the Python path to enable imports
        project_root = Path(__file__).parent
        if str(project_root) not in sys.path:
            sys.path.append(str(project_root))
        
        # Initialize knowledge base
        self._initialize_knowledge_base()
        
        # Process new documents in meus_arquivos/originais
        self._process_personal_documents()
        
        logger.info("System initialization completed")
    
    def _initialize_knowledge_base(self):
        """
        Initialize the knowledge base by creating the chroma_db if it doesn't exist.
        """
        try:
            from knowledge_base.create_kb import create_knowledge_base
            
            kb_path = Path("chroma_db")
            if not kb_path.exists() or not any(kb_path.iterdir()):
                logger.info("Knowledge base not found or empty. Creating new knowledge base...")
                create_knowledge_base()
                logger.info("Knowledge base created successfully")
            else:
                logger.info(f"Knowledge base found at {kb_path}")
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {e}")
            # Create a minimal knowledge base structure if the import fails
            kb_path = Path("chroma_db")
            kb_path.mkdir(exist_ok=True)
            logger.info("Created minimal knowledge base structure")
    
    def _process_personal_documents(self):
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
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
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
            raise
    
    def _initialize_db_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Initialize the DuckDB database connection.
        
        Returns:
            DuckDB connection object
        """
        try:
            if not self.db_dir.exists():
                self.db_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created database directory at {self.db_dir}")
            
            conn = duckdb.connect(str(self.duck_db_path))
            logger.info(f"Connected to DuckDB at {self.duck_db_path}")
            return conn
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def _register_resources(self):
        """Register all MCP resources."""
        
        @self.mcp.resource("declaracao://2025")
        def ler_declaracao_atual():
            """
            Reads the current tax declaration XML file.

            Returns:
                str: JSON representation of the tax declaration
            """
            try:
                ir_xml = Path.home() / self.config['IRPF_DIR_2025'] / "aplicacao" / "dados" / str(self.config['CPF']) / f"{self.config['CPF']}-0000000000.xml"
                logger.info(f"Reading declaration from {ir_xml}")
                
                if not ir_xml.exists():
                    logger.error(f"Declaration file not found: {ir_xml}")
                    return json.dumps({"error": "Declaration file not found"}, indent=2, ensure_ascii=False)
                
                decl = parse_irpf2025(ir_xml)
                return json.dumps(decl.model_dump(mode="json"), indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Error reading declaration: {e}")
                return json.dumps({"error": f"Failed to read declaration: {str(e)}"}, indent=2, ensure_ascii=False)
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        @self.mcp.tool()
        def verificar_status_declaracao():
            """
            Verifica se a declaração de imposto está disponível e acessível.
            
            Returns:
                dict: Status da declaração com informações básicas.
            """
            logger.info("Verificando status da declaração")
            try:
                # Try to access the XML file
                ir_xml = Path.home() / self.config['IRPF_DIR_2025'] / "aplicacao" / "dados" / str(self.config['CPF']) / f"{self.config['CPF']}-0000000000.xml"
                
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

        @self.mcp.tool()
        def query_irpf_db(sql_query: str):
            """
            Execute a SQL query against the IRPF DuckDB database.
            
            Args:
                sql_query (str): SQL query to execute
                
            Returns:
                pandas.DataFrame: Result of the query
            """
            try:
                logger.info(f"Executing SQL query: {sql_query}")
                return self.duck_conn.execute(sql_query).fetchdf()
            except Exception as e:
                logger.error(f"Error executing query: {e}")
                return pd.DataFrame()

        @self.mcp.tool()
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

        @self.mcp.tool()
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

        @self.mcp.tool()
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

        @self.mcp.tool()
        def all_income_sources():
            """
            Find all income sources across different categories.
            
            Returns:
                pandas.DataFrame: All income sources
            """
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
            logger.info("Finding all income sources")
            return query_irpf_db(query)

        @self.mcp.tool()
        def query_kb(query: str):
            """
            Query the IRPF knowledge base.
            
            Args:
                query (str): The query to search in the knowledge base
                
            Returns:
                str: Response from the knowledge base
            """
            try:
                logger.info(f"Querying knowledge base: {query}")
                # load from disk
                db2 = chromadb.PersistentClient(path="./chroma_db")
                chroma_collection = db2.get_or_create_collection("IRPF")
                vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
                index = VectorStoreIndex.from_vector_store(
                    vector_store,
                    embed_model=self.embed_model,
                )

                query_engine = index.as_query_engine()
                response = query_engine.query(query)
                return str(response)
            except Exception as e:
                logger.error(f"Error querying knowledge base: {e}")
                return f"Error querying knowledge base: {str(e)}"
    
    def run(self, server_type: str = "stdio", port: int = 3000):
        """
        Run the MCP server.
        
        Args:
            server_type: Type of server to run ("stdio" or "sse")
            port: Port to run the server on (for "sse" type)
        """
        logger.info(f"Starting IRPF MCP server with {server_type} interface")
        try:
            if server_type == "sse":
                self.mcp.run(server_type, port=port)
            else:
                self.mcp.run(server_type)
        except Exception as e:
            logger.error(f"Error running server: {e}")
            raise

def main():
    """Main entry point for the IRPF MCP server."""
    parser = argparse.ArgumentParser(description="IRPF MCP Server")
    parser.add_argument(
        "--server_type", type=str, default="stdio", choices=["sse", "stdio"],
        help="Type of server interface (sse or stdio)"
    )
    parser.add_argument(
        "--port", type=int, default=3000,
        help="Port to run the server on (for sse server type)"
    )
    parser.add_argument(
        "--config", type=str, default="setup.yaml",
        help="Path to configuration file"
    )
    
    args = parser.parse_args()
    
    print("🚀 Starting IRPF MCP server...")
    print(f"Server type: {args.server_type}")
    if args.server_type == "sse":
        print(f"Launching on Port: {args.port}")
        print(f'Check "http://localhost:{args.port}/sse" for the server status')
    
    server = IRPFMCPServer(config_path=args.config)
    server.run(args.server_type, args.port)

if __name__ == "__main__":
    main()
