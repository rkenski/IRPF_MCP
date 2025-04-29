# IRPF_MCP: Assistente Inteligente para Declaração de Imposto de Renda

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Status-Beta-orange.svg" alt="Status">
</p>

IRPF_MCP é um assistente inteligente baseado em IA para auxiliar contribuintes brasileiros com sua declaração de Imposto de Renda de Pessoa Física (IRPF). O sistema utiliza tecnologias avançadas de processamento de linguagem natural e análise de documentos para facilitar o preenchimento, verificação e otimização da declaração de imposto.

## 🌟 Características

- **Integração com o programa oficial da Receita Federal**: Lê e interpreta arquivos XML da declaração do IRPF diretamente do programa oficial
- **Processamento de documentos financeiros**: Extrai automaticamente informações de PDFs de informes de rendimentos, notas fiscais e outros documentos relevantes
- **Base de conhecimento fiscal**: Acessa informações atualizadas sobre legislação tributária e regras do IRPF
- **Análise de dados financeiros**: Organiza e analisa rendimentos, despesas, bens e direitos para otimizar a declaração
- **Interface conversacional**: Responde a perguntas sobre o imposto de renda em linguagem natural

## 🛠️ Tecnologias Utilizadas

- **FastMCP**: Framework para criação de assistentes inteligentes
- **LlamaIndex**: Para indexação e recuperação de informações da base de conhecimento
- **ChromaDB**: Banco de dados vetorial para armazenamento eficiente de embeddings
- **DuckDB**: Banco de dados analítico para processamento de dados financeiros
- **OpenAI**: Modelos de linguagem e embeddings para processamento de linguagem natural
- **LlamaParse**: Para extração precisa de informações de documentos PDF complexos

## 📋 Pré-requisitos

- Python 3.9 ou superior
- Programa IRPF 2025 da Receita Federal instalado
- Chave de API da OpenAI
- Chave de API da LlamaParse (para processamento de documentos)

## 🚀 Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/IRPF_MCP.git
   cd IRPF_MCP
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure o arquivo `setup.yaml` com suas informações:
   ```yaml
   CPF: seu_cpf_sem_pontuacao
   OPENAI_API_KEY: sua_chave_api_openai
   LLAMAPARSE_API_KEY: sua_chave_api_llamaparse
   IRPF_DIR_2025: /caminho/para/ProgramasRFB/IRPF2025
   ```

## 📊 Uso

1. Coloque seus documentos fiscais (PDFs de informes de rendimentos, etc.) na pasta `meus_arquivos/originais/`

2. Inicie o servidor:
   ```bash
   python server.py
   ```

3. Acesse o assistente através da interface web ou API

4. Exemplos de consultas que você pode fazer:
   - "Qual o total de rendimentos tributáveis que recebi no ano passado?"
   - "Quais despesas médicas posso deduzir?"
   - "Como declarar rendimentos de aluguel?"
   - "Verifique se há inconsistências na minha declaração"

## 📁 Estrutura do Projeto

- `server.py`: Servidor principal do IRPF_MCP
- `setup.yaml`: Arquivo de configuração
- `meus_arquivos/`: Diretório para documentos pessoais
  - `originais/`: PDFs e documentos originais
  - `data_files/`: Dados extraídos dos documentos
- `knowledge_base/`: Base de conhecimento sobre legislação tributária
- `database/`: Banco de dados DuckDB com informações processadas

## 🤝 Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

## 📄 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.

## ⚠️ Aviso Legal

Este software é fornecido apenas como uma ferramenta auxiliar e não substitui o aconselhamento profissional de um contador ou especialista em impostos. Os usuários são responsáveis pela precisão e conformidade de suas declarações de imposto de renda.

---

<p align="center">
  Desenvolvido com ❤️ para simplificar a vida dos contribuintes brasileiros
</p>
