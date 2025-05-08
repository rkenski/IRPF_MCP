#!/usr/bin/env python3
"""
Script para verificar o banco de dados DuckDB do IRPF MCP
"""
import duckdb
import pandas as pd
from pathlib import Path

# Caminho para o banco de dados
db_path = Path("/home/kenski/projects/IRPF_MCP/database/irpf_database.duckdb")

print(f"Verificando banco de dados em: {db_path}")
print(f"O arquivo existe? {db_path.exists()}")

if db_path.exists():
    print(f"Tamanho do arquivo: {db_path.stat().st_size} bytes")
    
    try:
        # Conectar ao banco de dados
        conn = duckdb.connect(str(db_path))
        print("Conexão estabelecida com sucesso!")
        
        # Listar todas as tabelas
        print("\nTabelas disponíveis:")
        tables_df = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchdf()
        print(tables_df)
        
        # Verificar se as tabelas de rendimentos existem
        income_tables = ["rendimentos_tributaveis_pj", "rendimentos_exclusivos", "rendimentos_isentos"]
        for table in income_tables:
            exists = conn.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main' AND table_name='{table}'").fetchone()[0]
            print(f"Tabela {table} existe? {exists > 0}")
        
        # Tentar consultar as fontes de receita
        print("\nConsultando fontes de receita:")
        try:
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
            
            result = conn.execute(query).fetchdf()
            print(result)
        except Exception as e:
            print(f"Erro ao consultar fontes de receita: {e}")
            
            # Verificar cada tabela individualmente
            for table in income_tables:
                try:
                    print(f"\nVerificando conteúdo da tabela {table}:")
                    table_exists = conn.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main' AND table_name='{table}'").fetchone()[0]
                    
                    if table_exists > 0:
                        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        print(f"Número de registros: {count}")
                        
                        if count > 0:
                            sample = conn.execute(f"SELECT * FROM {table} LIMIT 3").fetchdf()
                            print("Amostra de dados:")
                            print(sample)
                        else:
                            print("A tabela está vazia.")
                    else:
                        print("A tabela não existe.")
                except Exception as table_error:
                    print(f"Erro ao verificar tabela {table}: {table_error}")
        
        # Fechar a conexão
        conn.close()
        
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
else:
    print("O arquivo do banco de dados não existe!")
