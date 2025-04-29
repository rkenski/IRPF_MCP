'''
Esse script extrai as informações de arquivos PDF de declarações de IRPF e cria um banco de dados.
Ele está focado muito mais em precisão do que em velocidade.
O único parser que encontrei capaz de extrair as tabelas complexas de informes de rendimentos foi o Llamaparse.
Outros parsers muito bons, como Pypdf ou mesmo o Docling, sequer conseguiram encontrar o texto em alguns formulários da TOTVS, que dirá formatar corretamente as tabelas.
'''

from llama_index.core import SimpleDirectoryReader
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_cloud_services import LlamaParse
import nest_asyncio, os, json
from pathlib import Path
from tqdm import tqdm
from llama_index.core import SQLDatabase, SimpleDirectoryReader, Document
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.indices.struct_store import SQLTableRetrieverQueryEngine
import pandas as pd
from decimal import Decimal
import duckdb

def process_personal_documents(source_folder=None, force_processing=False):
    """
    Process personal documents from PDF files and create a database.
    
    Args:
        source_folder (Path or str, optional): Path to the folder containing personal documents.
                                              Defaults to "meus_arquivos" in the current directory.
        force_processing (bool, optional): Force processing even if no new files are detected.
                                          Defaults to False.
    
    Returns:
        bool: True if processing was performed, False otherwise
    """
    nest_asyncio.apply()
    
    # Set default source folder if not provided
    if source_folder is None:
        # Try to get the absolute path relative to the current file
        current_file_dir = Path(__file__).parent
        source_folder = current_file_dir
    elif isinstance(source_folder, str):
        source_folder = Path(source_folder)
        
    # Make sure we have an absolute path
    if not source_folder.is_absolute():
        source_folder = Path.cwd() / source_folder
        
    print(f"Using source folder: {source_folder}")

    data_files = source_folder / "data_files"
    data_files.mkdir(parents=True, exist_ok=True)

    # Ensure the originais directory exists
    originais_dir = source_folder / "originais"
    if not originais_dir.exists():
        originais_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created directory {originais_dir}")
        return False  # No processing needed for empty directory
    
    # Check if there are any files to process
    pdf_files = list(originais_dir.glob("*.pdf"))
    if not pdf_files and not force_processing:
        print("No PDF files found in Originais directory")
        return False
    
    parser = LlamaParse(
        num_workers=1,       
        verbose=True,
        language="pt",
        parse_mode="parse_page_with_lvm",
        do_not_cache=True)
    
    processed_marker = data_files / "from_pdf.json"
    
    # Check if processing is needed
    processing_needed = force_processing
    
    if not processed_marker.exists():
        print("No processed documents marker found. Processing needed.")
        processing_needed = True
    elif pdf_files:
        # Check if there are new files or modified files
        processed_time = processed_marker.stat().st_mtime
        
        for file_path in pdf_files:
            if file_path.stat().st_mtime > processed_time:
                print(f"New or modified file detected: {file_path}")
                processing_needed = True
                break
    
    if not processing_needed:
        print("All PDF files have already been processed")
        return False
    
    # Process the documents
    print("Processing personal documents...")
    
    if not processed_marker.exists():
        dir_reader = SimpleDirectoryReader(
            input_dir=originais_dir,
            file_extractor={".pdf": parser},
        ).load_data()
        # Ensure the data_files directory exists
        data_files.mkdir(parents=True, exist_ok=True)
        with open(processed_marker, "w") as f:
            json.dump([x.to_dict() for x in dir_reader], f, indent=4)
    else:
        with open(processed_marker, "r") as f:
            dir_reader = [Document.from_dict(x) for x in json.load(f)]
    
    from llama_index.llms.openai import OpenAI
    from IRPF_pydantic_schem_resumido import DeclaracaoIRPF2025
    
    llm = OpenAI(model="o4-mini-2025-04-16")
    sllm = llm.as_structured_llm(DeclaracaoIRPF2025)
    
    result = []
    for i in tqdm(dir_reader, total=len(dir_reader)):
        result.append(sllm.complete(i.text))
    
    irpf = [json.loads(x.text) for x in result]
    for i, resp in enumerate(irpf):
        for k, v in dir_reader[i].metadata.items():
            resp[k] = v
    
    # Convert irpf from json/dict into a queryable database using DuckDB
    
    # Helper that converts Decimal → float so databases are happy
    def dump(obj):
        if isinstance(obj, dict):
            d = obj.copy()
            for k, v in d.items():
                if isinstance(v, Decimal):
                    d[k] = float(v)
                elif isinstance(v, dict):
                    d[k] = dump(v)
                elif isinstance(v, list):
                    d[k] = [dump(item) for item in v]
            return d
        elif isinstance(obj, list):
            return [dump(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        else:
            return obj
    
    # Create database directory if it doesn't exist
    db_dir = Path("/home/kenski/projects/IRPF_MCP/database")
    db_dir.mkdir(exist_ok=True)
    
    # Create DataFrames for each type of data in the IRPF schema
    bens_df = pd.DataFrame([dump(item) for declaration in irpf for item in declaration.get('bens_direitos', [])])
    doacoes_df = pd.DataFrame([dump(item) for declaration in irpf for item in declaration.get('doacoes_efetuadas', [])])
    pagto_df = pd.DataFrame([dump(item) for declaration in irpf for item in declaration.get('pagamentos_efetuados', [])])
    rexcl_df = pd.DataFrame([dump(item) for declaration in irpf for item in declaration.get('rendimentos_exclusivos', [])])
    risento_df = pd.DataFrame([dump(item) for declaration in irpf for item in declaration.get('rendimentos_isentos', [])])
    rtrib_pj_df = pd.DataFrame([dump(item) for declaration in irpf for item in declaration.get('rendimentos_tributaveis_pj', [])])
    
    # Create empty DataFrames with correct schema if needed
    if bens_df.empty:
        bens_df = pd.DataFrame({
            'grupo': pd.Series(dtype='str'),
            'codigo': pd.Series(dtype='str'),
            'discriminacao': pd.Series(dtype='str'),
            'valor_2023': pd.Series(dtype='float'),
            'valor_2024': pd.Series(dtype='float'),
            'declaration_id': pd.Series(dtype='int')
        })
    
    if doacoes_df.empty:
        doacoes_df = pd.DataFrame({
            'codigo': pd.Series(dtype='str'),
            'cnpj_proponente': pd.Series(dtype='str'),
            'nome_proponente': pd.Series(dtype='str'),
            'valor_pago': pd.Series(dtype='float'),
            'declaration_id': pd.Series(dtype='int')
        })
    
    if pagto_df.empty:
        pagto_df = pd.DataFrame({
            'codigo': pd.Series(dtype='str'),
            'pessoa_beneficiada': pd.Series(dtype='str'),
            'cpf_prestador': pd.Series(dtype='str'),
            'nome_prestador': pd.Series(dtype='str'),
            'valor_pago': pd.Series(dtype='float'),
            'parcela_nao_dedutivel': pd.Series(dtype='float'),
            'declaration_id': pd.Series(dtype='int')
        })
    
    if rexcl_df.empty:
        rexcl_df = pd.DataFrame({
            'tipo_rendimento': pd.Series(dtype='str'),
            'tipo_beneficiario': pd.Series(dtype='str'),
            'cnpj_fonte_pagadora': pd.Series(dtype='str'),
            'nome_fonte_pagadora': pd.Series(dtype='str'),
            'valor': pd.Series(dtype='float'),
            'declaration_id': pd.Series(dtype='int')
        })
    
    if risento_df.empty:
        risento_df = pd.DataFrame({
            'tipo_rendimento': pd.Series(dtype='str'),
            'tipo_beneficiario': pd.Series(dtype='str'),
            'cnpj_fonte_pagadora': pd.Series(dtype='str'),
            'nome_fonte_pagadora': pd.Series(dtype='str'),
            'valor': pd.Series(dtype='float'),
            'declaration_id': pd.Series(dtype='int')
        })
    
    if rtrib_pj_df.empty:
        rtrib_pj_df = pd.DataFrame({
            'cpf_cnpj_fonte_pagadora': pd.Series(dtype='str'),
            'nome_fonte_pagadora': pd.Series(dtype='str'),
            'rendimentos': pd.Series(dtype='float'),
            'contribuicao_previdenciaria': pd.Series(dtype='float'),
            'imposto_retido': pd.Series(dtype='float'),
            'declaration_id': pd.Series(dtype='int')
        })
    
    # Create a declarations table with metadata and summary
    declarations_data = []
    for i, declaration in enumerate(irpf):
        declaration_data = {
            'declaration_id': i,
            'file_path': declaration.get('file_path', ''),
            'file_name': declaration.get('file_name', ''),
            'summary': declaration.get('summary', {}).get('text', '') if isinstance(declaration.get('summary', {}), dict) else ''
        }
        declarations_data.append(declaration_data)
        
    declarations_df = pd.DataFrame(declarations_data)
    
    # Add declaration_id to each DataFrame for joining
    for df_name, df in [
        ('bens_df', bens_df), 
        ('doacoes_df', doacoes_df), 
        ('pagto_df', pagto_df),
        ('rexcl_df', rexcl_df), 
        ('risento_df', risento_df), 
        ('rtrib_pj_df', rtrib_pj_df)
    ]:
        if not df.empty and 'declaration_id' not in df.columns:
            # For each item, assign the declaration ID based on its position in the flattened list
            df['declaration_id'] = df.index % len(irpf) if len(irpf) > 0 else 0
    
    # Create DuckDB database
    duck_db_path = db_dir / "irpf_database.duckdb"
    duck_conn = duckdb.connect(str(duck_db_path))
    
    # Register DataFrames as tables in DuckDB
    duck_conn.register('bens_df', bens_df)
    duck_conn.register('doacoes_df', doacoes_df)
    duck_conn.register('pagto_df', pagto_df)
    duck_conn.register('rexcl_df', rexcl_df)
    duck_conn.register('risento_df', risento_df)
    duck_conn.register('rtrib_pj_df', rtrib_pj_df)
    duck_conn.register('declarations_df', declarations_df)
    
    # Create persistent tables in the database
    duck_conn.execute("CREATE OR REPLACE TABLE bens_direitos AS SELECT * FROM bens_df")
    duck_conn.execute("CREATE OR REPLACE TABLE doacoes_efetuadas AS SELECT * FROM doacoes_df")
    duck_conn.execute("CREATE OR REPLACE TABLE pagamentos_efetuados AS SELECT * FROM pagto_df")
    duck_conn.execute("CREATE OR REPLACE TABLE rendimentos_exclusivos AS SELECT * FROM rexcl_df")
    duck_conn.execute("CREATE OR REPLACE TABLE rendimentos_isentos AS SELECT * FROM risento_df")
    duck_conn.execute("CREATE OR REPLACE TABLE rendimentos_tributaveis_pj AS SELECT * FROM rtrib_pj_df")
    duck_conn.execute("CREATE OR REPLACE TABLE declarations AS SELECT * FROM declarations_df")
    
    print(f"DuckDB database created at: {duck_db_path}")
    return True

def query_irpf_db(sql_query):
    """
    Execute a SQL query against the IRPF DuckDB database.
    
    Args:
        sql_query (str): SQL query to execute
        
    Returns:
        pandas.DataFrame: Result of the query
    """
    db_dir = Path("/home/kenski/projects/IRPF_MCP/database")
    duck_db_path = db_dir / "irpf_database.duckdb"
    
    if not duck_db_path.exists():
        print(f"Database file not found at {duck_db_path}")
        return pd.DataFrame()
    
    try:
        conn = duckdb.connect(str(duck_db_path))
        return conn.execute(sql_query).fetchdf()
    except Exception as e:
        print(f"Error executing query: {e}")
        return pd.DataFrame()

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
    return query_irpf_db(query)

def total_payments_by_category():
    """
    Calculate total payments by category.
    
    Returns:
        pandas.DataFrame: Total payments by category
    """
    query = """
    SELECT codigo, SUM(valor_pago) as total_pago
    FROM pagamentos_efetuados
    GROUP BY codigo
    ORDER BY total_pago DESC
    """
    return query_irpf_db(query)

def analyze_assets():
    """
    Analyze assets by group and calculate value changes.
    
    Returns:
        pandas.DataFrame: Asset analysis
    """
    query = """
    SELECT 
        grupo, 
        COUNT(*) as num_assets,
        SUM(valor_2023) as total_2023,
        SUM(valor_2024) as total_2024,
        SUM(valor_2024 - valor_2023) as value_change,
        (SUM(valor_2024) - SUM(valor_2023)) / NULLIF(SUM(valor_2023), 0) * 100 as percent_change
    FROM bens_direitos
    GROUP BY grupo
    ORDER BY total_2024 DESC
    """
    return query_irpf_db(query)

def all_income_sources():
    """
    Find all income sources across different income types.
    
    Returns:
        pandas.DataFrame: All income sources
    """
    query = """
    WITH 
    tributaveis AS (
        SELECT 
            'Tributável' as tipo_rendimento,
            nome_fonte_pagadora,
            rendimentos as valor
        FROM rendimentos_tributaveis_pj
    ),
    isentos AS (
        SELECT 
            'Isento' as tipo_rendimento,
            nome_fonte_pagadora,
            valor
        FROM rendimentos_isentos
    ),
    exclusivos AS (
        SELECT 
            'Exclusivo' as tipo_rendimento,
            nome_fonte_pagadora,
            valor
        FROM rendimentos_exclusivos
    ),
    all_sources AS (
        SELECT * FROM tributaveis
        UNION ALL
        SELECT * FROM isentos
        UNION ALL
        SELECT * FROM exclusivos
    )
    SELECT 
        nome_fonte_pagadora,
        tipo_rendimento,
        SUM(valor) as total_valor
    FROM all_sources
    GROUP BY nome_fonte_pagadora, tipo_rendimento
    ORDER BY total_valor DESC
    """
    return query_irpf_db(query)

# Run the processing if this file is executed directly
if __name__ == "__main__":
    processed = process_personal_documents()
    
    if processed:
        print("\nExample query - Salary income:")
        print(find_salary_income())
        
        print("\nExample query - Total payments by category:")
        print(total_payments_by_category())
        
        print("\nExample query - Asset analysis:")
        print(analyze_assets())
        
        print("\nExample query - All income sources:")
        print(all_income_sources())
