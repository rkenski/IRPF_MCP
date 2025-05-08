from mcp.server.fastmcp import FastMCP
from pathlib import Path
import yaml
import logging
import sys
import os
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mcp_server.log"),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("IRPF_MCP")

# Setup
logger.info("Starting MCP server for IRPF_POC")
mcp = FastMCP("IRPF_POC")

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "setup.yaml")

logger.info(f"Loading config from {config_path}")
try:
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    logger.info(f"Config loaded successfully: {config}")
except Exception as e:
    logger.error(f"Failed to load config: {e}")
    raise

@mcp.resource("declaracao://2025")
def ler_declaracao_atual():
    """Lê o XML da declaração de 2025.

    Retorna:
        str: XML content.
    """
    logger.info("Attempting to read declaration XML")
    
    ir_xml = Path.home() / config['IRPF_DIR_2025'] / "aplicacao" / "dados" / str(config['CPF']) / f"{config['CPF']}-0000000000.xml"
    logger.info(f"XML path: {ir_xml}")
    
    try:
        with open(ir_xml, "r") as f:
            content = f.read()
            logger.info(f"Successfully read XML ({len(content)} characters)")
            return content
    except Exception as e:
        logger.error(f"Error reading XML: {e}")
        raise

@mcp.tool()
def obter_resumo_declaracao():
    """Retorna um resumo da declaração de imposto de renda atual.
    
    Returns:
        dict: Um resumo com informações principais da declaração.
    """
    logger.info("Obtendo resumo da declaração")
    try:
        # Get the XML content using our resource
        xml_content = ler_declaracao_atual()
        
        # Parse the XML
        root = ET.fromstring(xml_content)
        
        # Extract basic information (adapt based on actual XML structure)
        # This is a simplified example - adjust according to actual XML structure
        try:
            cpf = root.find(".//CPF").text if root.find(".//CPF") is not None else "N/A"
        except:
            cpf = config['CPF']  # Fallback to config value
            
        try:
            nome = root.find(".//nome").text if root.find(".//nome") is not None else "N/A"
        except:
            nome = "Nome não encontrado"
            
        # Try to find rendimentos (adapt to actual XML structure)
        rendimentos = []
        try:
            for rendimento in root.findall(".//rendimento"):
                fonte = rendimento.find("fonte").text if rendimento.find("fonte") is not None else "Desconhecido"
                valor = rendimento.find("valor").text if rendimento.find("valor") is not None else "0.00"
                rendimentos.append({"fonte": fonte, "valor": valor})
        except:
            rendimentos = [{"fonte": "XML structure mismatch", "valor": "0.00"}]
        
        # Return a summary
        resumo = {
            "cpf": cpf,
            "nome": nome,
            "ano_calendario": "2024",
            "ano_exercicio": "2025",
            "rendimentos": rendimentos,
            "mensagem": "Resumo extraído com sucesso da declaração IRPF"
        }
        
        logger.info(f"Resumo obtido com sucesso: {resumo}")
        return resumo
        
    except Exception as e:
        logger.error(f"Erro ao obter resumo: {e}")
        return {
            "erro": f"Não foi possível obter o resumo da declaração: {str(e)}",
            "mensagem": "Falha ao processar a declaração IRPF"
        }

@mcp.tool()
def verificar_status_declaracao():
    """Verifica se a declaração de imposto está disponível e acessível.
    
    Returns:
        dict: Status da declaração com informações básicas.
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

if __name__ == "__main__":
    # Start the server
    logger.info("🚀 Starting MCP server on stdio...")
    try:
        mcp.run("stdio")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        raise