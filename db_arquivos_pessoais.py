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

nest_asyncio.apply()

SOURCE_FOLDER = Path("/home/kenski/projects/IRPF_MCP/meus_arquivos")
GEN_MODEL = OpenAI(model="gpt-4.1")
EMBED_MODEL = OpenAIEmbedding(model="text-embedding-3-large")
QUERY = "Há algum rendimento de salário? Qual?"

parser = LlamaParse(
    num_workers=1,       # if multiple files passed, split in `num_workers` API calls
    verbose=True,
    language="pt",
    parse_mode="parse_page_with_lvm",
    do_not_cache=True)

if not (SOURCE_FOLDER / "from_pdf.json").exists():
    dir_reader = SimpleDirectoryReader(
        input_dir=SOURCE_FOLDER/ "Originais",
        file_extractor={".pdf": parser},
    ).load_data()
    with open(SOURCE_FOLDER / "from_pdf.json", "w") as f:
        json.dump([x.to_dict() for x in dir_reader], f, indent=4)
else:
    with open(SOURCE_FOLDER / "from_pdf.json", "r") as f:
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
import pandas as pd
from decimal import Decimal
import duckdb
import os

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

# Create a function to query the DuckDB database
def query_irpf_db(sql_query):
    """
    Execute a SQL query against the IRPF DuckDB database.
    
    Args:
        sql_query (str): SQL query to execute
        
    Returns:
        pandas.DataFrame: Result of the query
    """
    try:
        return duck_conn.execute(sql_query).fetchdf()
    except Exception as e:
        print(f"Error executing query: {e}")
        return pd.DataFrame()

# Example query: Find all salary income
def find_salary_income():
    query = """
    SELECT d.file_name, r.nome_fonte_pagadora, r.rendimentos
    FROM rendimentos_tributaveis_pj r
    JOIN declarations d ON r.declaration_id = d.declaration_id
    ORDER BY r.rendimentos DESC
    """
    return query_irpf_db(query)

# Example query: Total payments by category
def total_payments_by_category():
    query = """
    SELECT codigo, SUM(valor_pago) as total_value
    FROM pagamentos_efetuados
    GROUP BY codigo
    ORDER BY total_value DESC
    """
    return query_irpf_db(query)

# Example query: Complex analytics with aggregation functions
def analyze_assets():
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
    return query_irpf_db(query)

# Example query: Find all income sources
def all_income_sources():
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
    return query_irpf_db(query)

print(f"DuckDB database created at: {duck_db_path}")
print("\nExample query - Salary income:")
print(find_salary_income())
print("\nExample query - Total payments by category:")
print(total_payments_by_category())
print("\nExample query - Asset analysis by group:")
print(analyze_assets())
print("\nExample query - All income sources:")
print(all_income_sources())

# Keep connection open for interactive use
# To close it later: duck_conn.close()

# Also save as Parquet files for additional flexibility
parquet_dir = db_dir / "parquet"
parquet_dir.mkdir(exist_ok=True)

if not bens_df.empty:
    bens_df.to_parquet(parquet_dir / "bens_direitos.parquet")
if not doacoes_df.empty:
    doacoes_df.to_parquet(parquet_dir / "doacoes_efetuadas.parquet")
if not pagto_df.empty:
    pagto_df.to_parquet(parquet_dir / "pagamentos_efetuados.parquet")
if not rexcl_df.empty:
    rexcl_df.to_parquet(parquet_dir / "rendimentos_exclusivos.parquet")
if not risento_df.empty:
    risento_df.to_parquet(parquet_dir / "rendimentos_isentos.parquet")
if not rtrib_pj_df.empty:
    rtrib_pj_df.to_parquet(parquet_dir / "rendimentos_tributaveis_pj.parquet")
declarations_df.to_parquet(parquet_dir / "declarations.parquet")

print(f"\nParquet files also created in: {parquet_dir}")
