from mcp.server.fastmcp import FastMCP
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.readers.docling import DoclingReader
from pathlib import Path
import yaml


#Setup Básico
mcp = FastMCP("IRPF_MCP")
with open("setup.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

'''
Resources: 
- Declaração de IR (IRPF) - OK
- Full docs db
- Docs vector db

Tools:
- IR KB
    - Docs da receita em vector database
    - Custom sources
'''

@mcp.resource("declaracao://2025")
def ler_declaracao_atual():
    """Reads the XML file.

    Returns:
        dict: XML content.
    """
    ir_xml = Path.home() / config['IRPF_DIR_2025'] / "aplicacao" / "dados" / str(config['CPF']) / f"{config['CPF']}-0000000000.xml"
    with open(ir_xml, "r") as f:
        return f.read()

@mcp.resource("declaracao://schema")
def ler_schema_declaracao():
    """Reads the XML schema file.

    Returns:
        dict: XML schema content.
    """
    with open("schema.txt", "r") as f:
        return f.read()

def criar_db_documentos(doc_folder):
    reader = DoclingReader()
    node_parser = MarkdownNodeParser()

    index = VectorStoreIndex.from_documents(
        documents=reader.load_data(SOURCE),
        transformations=[node_parser],
        embed_model=EMBED_MODEL,
    )
    result = index.as_query_engine(llm=GEN_MODEL).query(QUERY)
    print(f"Q: {QUERY}\nA: {result.response.strip()}\n\nSources:")
    display([(n.text, n.metadata) for n in result.source_nodes])

    pass

def baixar_textos_receita():
    pass

def criar_kb_vector_store():
    pass





'''@mcp.tool()
def read_xml():
    """Reads the XML file.

    Returns:
        dict: XML content.
    """
    with open("XML_file", "r") as f:
        return f.read()
'''

if __name__ == "__main__":
    # Start the server
    print("🚀Starting server... ")

    '''parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server_type", type=str, default="stdio", choices=["sse", "stdio"]
    )
    print("Server type: ", parser.parse_args().server_type)
    print("Launching on Port: ", 3000)
    print('Check "http://localhost:3000/sse" for the server status')

    args = parser.parse_args()
    '''
    mcp.run("stdio")



'ProgramasRFB/IRPF2025/aplicacao/dados/30390505838/30390505838-0000000000.xml'