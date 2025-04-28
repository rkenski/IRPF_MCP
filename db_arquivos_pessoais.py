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

result_text = [json.loads(x.text) for x in response]
for i, resp in enumerate(response_text):
    for k, v in dir_reader[i].metadata.items():
        resp[k] = v


#CREATE DB
import pandas as pd
from decimal import Decimal

# ── assume `irpf` is an instance of DeclaracaoIRPF2025 ──────────────────────
# Helper that converts Decimal → float so pandas/Arrow/Parquet are happy
def dump(obj):
    d = obj.model_dump()
    for k, v in d.items():
        if isinstance(v, Decimal):
            d[k] = float(v)
    return d

bens_df       = pd.DataFrame([dump(b) for b in irpf.bens_direitos])
doacoes_df    = pd.DataFrame([dump(d) for d in irpf.doacoes_efetuadas])
pagto_df      = pd.DataFrame([dump(p) for p in irpf.pagamentos_efetuados])
rexcl_df      = pd.DataFrame([dump(r) for r in irpf.rendimentos_exclusivos])
risento_df    = pd.DataFrame([dump(r) for r in irpf.rendimentos_isentos])
rtrib_pj_df   = pd.DataFrame([dump(r) for r in irpf.rendimentos_tributaveis_pj])

# optional: write to Arrow/Parquet for zero-copy DuckDB queries
bens_df.to_parquet("bens_direitos.parquet")     # repeat for each DF








































result = index.as_query_engine(llm=GEN_MODEL).query(QUERY)
print(f"Q: {QUERY}\nA: {result.response.strip()}\n\nSources:")
display([(n.text, n.metadata) for n in result.source_nodes])
