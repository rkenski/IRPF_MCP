from mcp.server.fastmcp import FastMCP
import yaml


mcp = FastMCP("IRPF_MCP")
with open("setup.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

print(config)

'''
Resources: 
- Declaração de IR (IRPF)
- Lista de documentos disponíveis (get_document)

Tools:
- IR KB
    - Docs da receita
    - Custom sources
'''

@mcp.resource("declaracao://2025")
def ler_declaracao():
    """Reads the XML file.

    Returns:
        dict: XML content.
    """
    ir_xml = f"{config['IRPF_DIR_2025']}/aplicacao/dados/{config['CPF']}/{config['CPF']}-0000000000.xml"
    with open(ir_xml, "r") as f:
        return f.read()
    with open(ir_xml, "r") as f:
        ir= f.read()


@mcp.resource()
def read_schema():
    """Reads the XML schema file.

    Returns:
        dict: XML schema content.
    """
    with open("schema.txt", "r") as f:
        return f.read()

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