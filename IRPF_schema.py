from decimal import Decimal
from datetime import date
from typing import Literal, Optional, List
from pydantic import BaseModel, Field, condecimal, field_validator, model_validator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# 2-decimal-places currency limited to R$ 999 999 999 999,99
Money = condecimal(max_digits=14, decimal_places=2)

def _only_digits(v: str) -> str:
    """Remove dots/dashes/spaces → keep just digits (useful for CPF/CNPJ)."""
    return "".join(ch for ch in v if ch.isdigit())

# ---------------------------------------------------------------------------
# 1.  Novo Bem e Direito  -----------------------------------------------------
# ---------------------------------------------------------------------------
class BemDireito(BaseModel):
    """
    “Bens e Direitos” schedule (Assets and Rights) – each instance represents
    a single asset line in the IRPF return.
    """

    grupo: str = Field(
        ...,
        description=(
            "Código do grupo de bens (ex.: '01', '02', '03'…). "
            "O próprio programa lista as opções."
        ),
    )
    codigo: str = Field(
        ...,
        description=(
            "Código específico do bem dentro do grupo (ex.: '01', '11', '13'…)."
        ),
    )
    pais: str = Field(
        "105",
        description="País onde o bem está localizado (código de três dígitos).",
        alias="localizacao_pais",
    )
    discriminacao: str = Field(
        ...,
        description="Campo de texto livre com a descrição detalhada do bem.",
    )
    valor_2023: Money = Field(
        ...,
        description="Situação em 31/12/2023 (valor do bem nessa data).",
        alias="situacao_31_12_2023",
    )
    valor_2024: Money = Field(
        ...,
        description="Situação em 31/12/2024 (valor do bem nessa data).",
        alias="situacao_31_12_2024",
    )
    repetir_valor: bool = Field(
        False,
        description=(
            "Se True, indica que o valor de 2023 foi repetido em 2024 usando "
            "o botão 'Repetir' do programa."
        ),
    )

    # Nice-to-have field_validator
    @model_validator(mode="before")
    def copy_valor(cls, data: dict):
        if data.get("repetir_valor") and not data.get("valor_2024"):
            data["valor_2024"] = data["valor_2023"]
        return data


# ---------------------------------------------------------------------------
# 2.  Nova Doação Efetuada  ---------------------------------------------------
# ---------------------------------------------------------------------------
class DoacaoEfetuada(BaseModel):
    """
    Ficha “Doações Efetuadas” – deduções incentivadas ou voluntárias.
    """

    codigo: str = Field(
        ...,
        description=(
            "Código da doação (ex.: '43 - Incentivo ao desporto', '40 - Fundo "
            "da criança e do adolescente' etc.)."
        ),
    )
    cnpj_proponente: Optional[str] = Field(
        None,
        description="CNPJ do proponente do projeto (quando exigido).",
    )
    nome_proponente: Optional[str] = Field(
        None,
        description="Nome/Razão social do proponente.",
    )
    valor_pago: Money = Field(
        ...,
        description="Valor efetivamente pago em 2024.",
    )


# ---------------------------------------------------------------------------
# 3.  Novo Pagamento Efetuado  ------------------------------------------------
# ---------------------------------------------------------------------------
class PagamentoEfetuado(BaseModel):
    codigo: str
    cpf_beneficiario: str = Field(..., min_length=11, max_length=14)  # 11 digits
    nome_beneficiario: Optional[str] = None

    cpf_cnpj_prestador: Optional[str] = None
    nome_prestador: Optional[str] = None
    descricao: Optional[str] = None

    valor_pago: Money
    parcela_nao_dedutivel: Money = Decimal("0.00")

    @field_validator("cpf_beneficiario", "cpf_cnpj_prestador", mode="before")
    def digits_only(cls, v):
        return _only_digits(v)

# ---------------------------------------------------------------------------
# 4.  Rendimento Sujeito à Tributação Exclusiva/Definitiva  ------------------
# ---------------------------------------------------------------------------
class RendExclusivo(BaseModel):
    """
    Ficha “Rendimentos Sujeitos à Tributação Exclusiva/Definitiva”.
    """

    tipo_rendimento: str = Field(
        ...,
        description="Código do rendimento (ex.: '06 - Aplicações financeiras').",
    )

    beneficiario: Optional[str] = Field(
        None,
        description="Nome do beneficiário (se dependente/alimentando).",
    )

    cpf_beneficiario: str = Field(
        ..., min_length=11,
        max_length=14,
        description='CPF do beneficiário do rendimento')

    cnpj_fonte_pagadora: str = Field(
        ...,
        description="CNPJ da fonte pagadora.",
    )
    nome_fonte_pagadora: str = Field(
        ...,
        description="Nome da fonte pagadora.",
    )
    valor: Money = Field(
        ...,
        description="Valor bruto tributado de forma exclusiva/definitiva.",
    )

    @field_validator(
        "cpf_beneficiario", "cnpj_fonte_pagadora", mode="before"
    )
    def digits_only(cls, v):
        return _only_digits(v)


# ---------------------------------------------------------------------------
# 5.  Rendimento Isento e Não Tributável  ------------------------------------
# ---------------------------------------------------------------------------
class RendIsento(BaseModel):
    """
    Ficha “Rendimentos Isentos e Não Tributáveis”.
    """

    tipo_rendimento: str = Field(
        ...,
        description="Código do rendimento (ex.: '01 - Bolsas de estudo').",
    )

    beneficiario: Optional[str] = Field(
        None,
        description="Nome do beneficiário (se dependente/alimentando).",
    )

    cpf_beneficiario: str = Field(
        ..., min_length=11,
        max_length=14,
        description='CPF do beneficiário do rendimento')


    cnpj_fonte_pagadora: Optional[str] = Field(
        None,
        description="CNPJ da fonte pagadora, quando existir.",
    )
    nome_fonte_pagadora: Optional[str] = Field(
        None,
        description="Nome da fonte pagadora.",
    )
    valor: Money = Field(
        ...,
        description="Valor isento recebido.",
    )

    @field_validator("cpf_beneficiario", "cnpj_fonte_pagadora", mode="before")
    def digits_only(cls, v):
        return _only_digits(v)

# ---------------------------------------------------------------------------
# 6.  Rendimento Tributável de Pessoa Jurídica  ------------------------------
# ---------------------------------------------------------------------------
class RendTribPJ(BaseModel):
    """
    Ficha “Rendimentos Tributáveis Recebidos de Pessoa Jurídica”.
    """

    cpf_cnpj_fonte_pagadora: str = Field(
        ...,
        description="CPF/CNPJ da fonte pagadora.",
    )
    nome_fonte_pagadora: str = Field(
        ...,
        description="Nome da fonte pagadora.",
    )

    beneficiario: Optional[str] = Field(
        None,
        description="Nome do beneficiário (se dependente/alimentando).",
    )

    cpf_beneficiario: str = Field(
        ..., min_length=11,
        max_length=14,
        description='CPF do beneficiário do rendimento')

    rendimentos: Money = Field(
        ...,
        description="Total de rendimentos tributáveis (salário, pró-labore etc.).",
    )
    contribuicao_previdenciaria: Money = Field(
        Decimal("0.00"),
        description="Contribuição ao INSS retida na fonte (oficial).",
    )
    imposto_retido: Money = Field(
        Decimal("0.00"),
        description="IRRF retido mensalmente pela fonte pagadora.",
    )
    decimo_terceiro: Money = Field(
        Decimal("0.00"),
        description="Valor do 13º salário recebido.",
        alias="decimo_terceiro_salario",
    )
    irrf_decimo_terceiro: Money = Field(
        Decimal("0.00"),
        description="IRRF retido sobre o 13º salário.",
    )


    @field_validator("cpf_cnpj_fonte_pagadora", mode="before")
    def digits_only(cls, v):
        return _only_digits(v)

class Summary(BaseModel):
    text: str = Field(
        ...,
        min_length=1,                 
        description="Resumo de até um parágrafo da declaração.",
    )

    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if isinstance(v, str):
            return cls(text=v)
        return v

# ---------------------------------------------------------------------------
# 7.  Declaração IRPF-2025  (master container)  ------------------------------
# ---------------------------------------------------------------------------

class DeclaracaoIRPF2025(BaseModel):
    """
    Modelo-raiz que agrega todas as fichas da declaração do Imposto de Renda
    da Pessoa Física – ano-base 2024 (programa IRPF 2025).

    Cada atributo é uma lista porque, no próprio software da Receita Federal,
    você pode inserir vários registros em cada ficha.
    """

    bens_direitos: List[BemDireito] = Field(
        default_factory=list,
        description="Ficha 'Bens e Direitos' – um item por bem ou direito.",
    )

    data_documento: date = Field(
        ...,
        description="Data em que o documento foi gerado (ou o ano a que se refere).",
    )

    doacoes_efetuadas: List[DoacaoEfetuada] = Field(
        default_factory=list,
        description="Ficha 'Doações Efetuadas' – um item por doação.",
    )

    pagamentos_efetuados: List[PagamentoEfetuado] = Field(
        default_factory=list,
        description="Ficha 'Pagamentos Efetuados' – despesas dedutíveis ou informativas.",
    )

    rendimentos_exclusivos: List[RendExclusivo] = Field(
        default_factory=list,
        description=(
            "Ficha 'Rendimentos Sujeitos à Tributação Exclusiva/Definitiva'."
        ),
    )

    rendimentos_isentos: List[RendIsento] = Field(
        default_factory=list,
        description="Ficha 'Rendimentos Isentos e Não Tributáveis'.",
    )

    rendimentos_tributaveis_pj: List[RendTribPJ] = Field(
        default_factory=list,
        description=(
            "Ficha 'Rendimentos Tributáveis Recebidos de Pessoa Jurídica'."
        ),
    )

    summary: Summary = Field(
        ...,
        description="Objeto Summary contendo o resumo da declaração.",
    )

DeclaracaoIRPF2025.model_rebuild()