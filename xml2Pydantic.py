#!/usr/bin/env python3
"""
irpf2025_parser.py

Parse an XML file produced by the Receita Federal IRPF-2025 program
and return a DeclaracaoIRPF2025 Pydantic object.

Usage
-----
>>> from irpf2025_parser import parse_irpf2025
>>> decl = parse_irpf2025("XML_DA_RECEITA.xml")
>>> print(decl.model_dump_json(indent=2, ensure_ascii=False))
"""

from __future__ import annotations

from lxml import etree as ET
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

from IRPF_pydantic_schem_resumido import (
    BemDireito,
    DeclaracaoIRPF2025,
    DoacaoEfetuada,
    Money,
    PagamentoEfetuado,
    RendExclusivo,
    RendIsento,
    RendTribPJ,
    Summary,
    TitDepAli,
)

# ────────────────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────────────────

def parse_money(raw: str | None) -> Money:
    raw = (raw or "0,00").strip()
    clean = raw.replace(".", "").replace(",", ".")
    return Money(Decimal(clean))



BENEFICIARIO_MAP: Dict[str, TitDepAli] = {
    "T": "titular",
    "D": "dependente",
    "A": "alimentando",
    "V": "alimentando",  # 'V' (voluntário) appears for alimentandos às vezes
}


def beneficiario_from_flag(flag: str | None) -> TitDepAli:
    return BENEFICIARIO_MAP.get((flag or "T").upper(), "titular")  # default titular


def normalise_codigo(cod: str) -> str:
    """Pad codes with zeros so they always have two digits ('1' → '01')."""
    return cod.zfill(2) if cod else cod


# ────────────────────────────────────────────────────────────────────────────────
#  Low-level find helpers
# ────────────────────────────────────────────────────────────────────────────────


def first_attrib(el: ET.Element, *attrs: str, default: str | None = None) -> str | None:
    """Return the first non-empty attribute among *attrs* (or *default*)."""
    for a in attrs:
        v = el.attrib.get(a)
        if v:
            return v
    return default


# ────────────────────────────────────────────────────────────────────────────────
#  Parsers for each schedule
# ────────────────────────────────────────────────────────────────────────────────


def parse_bens(root: ET.Element, ns: dict[str, str]) -> list[BemDireito]:
    bens: list[BemDireito] = []
    for item in root.findall(".//rf:bens/rf:item", ns):
        grupo  = (item.attrib.get("grupo")  or "").strip()
        codigo = (item.attrib.get("codigo") or "").strip()

        # se for o placeholder vazio, apenas atribua códigos neutros
        if not grupo or not codigo:
            grupo  = grupo  or "00"
            codigo = codigo or "00"

        bens.append(
            BemDireito(
                grupo=normalise_codigo(grupo),
                codigo=normalise_codigo(codigo),
                pais=item.attrib.get("pais", "105"),
                discriminacao=(item.attrib.get("discriminacao") or "").strip(),
                situacao_31_12_2023=parse_money(item.attrib.get("valorExercicioAnterior")),
                situacao_31_12_2024=parse_money(item.attrib.get("valorExercicioAtual")),
                repetir_valor=False,
            )
        )

    return bens

def parse_pagamentos(root: ET.Element, ns: Dict[str, str]) -> List[PagamentoEfetuado]:
    pags: List[PagamentoEfetuado] = []
    for item in root.findall(".//rf:pagamentos/rf:item", ns):
        pags.append(
            PagamentoEfetuado(
                codigo=normalise_codigo(item.attrib.get("codigo", "")),
                pessoa_beneficiada=beneficiario_from_flag(item.attrib.get("tipo")),
                cpf_cnpj_prestador=first_attrib(item, "niBeneficiario", "cpfPrestador"),
                nome_prestador=first_attrib(item, "nomeBeneficiario", "nomePrestador"),
                descricao=item.attrib.get("descricao") or None,
                valor_pago=parse_money(item.attrib.get("valorPago")),
                parcela_nao_dedutivel=parse_money(item.attrib.get("parcelaNaoDedutivel")),
            )
        )
    return pags


def parse_doacoes(root: ET.Element, ns: Dict[str, str]) -> List[DoacaoEfetuada]:
    doacoes: List[DoacaoEfetuada] = []
    for item in root.findall(".//rf:doacoes/rf:item", ns):
        doacoes.append(
            DoacaoEfetuada(
                codigo=item.attrib.get("codigo", ""),
                cnpj_proponente=item.attrib.get("cnpjProponente"),
                nome_proponente=item.attrib.get("nomeProponente"),
                valor_pago=parse_money(item.attrib.get("valorPago")),
            )
        )
    return doacoes


def parse_rend_trib_pj(root: ET.Element, ns: Dict[str, str]) -> List[RendTribPJ]:
    rend: List[RendTribPJ] = []
    titular_path = ".//rf:colecaoRendPJTitular/rf:item"
    depend_path = ".//rf:colecaoRendPJDependente/rf:item"
    for item in root.findall(f"{titular_path}|{depend_path}", ns):
        rend.append(
            RendTribPJ(
                cpf_cnpj_fonte_pagadora=item.attrib["NIFontePagadora"],
                nome_fonte_pagadora=item.attrib["nomeFontePagadora"],
                rendimentos=parse_money(item.attrib.get("rendRecebidoPJ")),
                contribuicao_previdenciaria=parse_money(
                    item.attrib.get("contribuicaoPrevOficial")
                ),
                imposto_retido=parse_money(item.attrib.get("impostoRetidoFonte")),
                decimo_terceiro=parse_money(item.attrib.get("decimoTerceiro")),
                irrf_decimo_terceiro=parse_money(item.attrib.get("IRRFDecimoTerceiro")),
            )
        )
    return rend


def parse_rend_isentos(root: ET.Element, ns: dict[str, str]) -> list[RendIsento]:
    isentos: list[RendIsento] = []
    for quadro in root.findall(".//rf:rendIsentos//*", ns):
        if quadro.tag.endswith("QuadroAuxiliar"):
            tipo = quadro.tag.split('}', 1)[-1]
            for item in quadro.findall("rf:item", ns):
                isentos.append(
                    RendIsento(
                        tipo_rendimento=tipo,
                        tipo_beneficiario=beneficiario_from_flag(item.attrib.get("tipoBeneficiario")),
                        beneficiario=item.attrib.get("cpfBeneficiario"),
                        cnpj_fonte_pagadora=item.attrib.get("cnpjEmpresa"),
                        nome_fonte_pagadora=first_attrib(item, "nomeFonte", "descricaoRendimento"),
                        valor=parse_money(item.attrib.get("valor")),
                    )
                )
    return isentos

def parse_rend_exclusivos(root: ET.Element, ns: Dict[str, str]) -> List[RendExclusivo]:
    exclusivos: List[RendExclusivo] = []
    for section in root.findall(".//rf:rendTributacaoExclusiva", ns):
        for item in section.findall(".//rf:item", ns):
            tipo = item.getparent().tag.split("}", 1)[-1]  # e.g. 'rendAplicacoesQuadroAuxiliar'
            exclusivos.append(
                RendExclusivo(
                    tipo_rendimento=tipo,
                    tipo_beneficiario=beneficiario_from_flag(item.attrib.get("tipoBeneficiario")),
                    beneficiario=item.attrib.get("cpfBeneficiario"),
                    cnpj_fonte_pagadora=item.attrib.get("cnpjEmpresa"),
                    nome_fonte_pagadora=item.attrib.get("nomeFonte"),
                    valor=parse_money(item.attrib.get("valor")),
                )
            )
    return exclusivos


# ────────────────────────────────────────────────────────────────────────────────
#  Top-level entry point
# ────────────────────────────────────────────────────────────────────────────────


def parse_irpf2025(xml_file: str | Path) -> DeclaracaoIRPF2025:
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # default namespace declared at the root
    ns = {"rf": root.tag.split("}")[0].strip("{")}

    bens = parse_bens(root, ns)
    pagamentos = parse_pagamentos(root, ns)
    doacoes = parse_doacoes(root, ns)
    rend_trib_pj = parse_rend_trib_pj(root, ns)
    rend_isentos = parse_rend_isentos(root, ns)
    rend_exclusivos = parse_rend_exclusivos(root, ns)

    # Simple one-line summary
    ident = root.find(".//rf:identificadorDeclaracao", ns)
    cpf = ident.attrib.get("cpf", "???") if ident is not None else "???"
    nome = ident.attrib.get("nome", "declarante") if ident is not None else "declarante"
    resumo = Summary(text=f"Declaração IRPF-2025 de {nome} (CPF {cpf}).")

    return DeclaracaoIRPF2025(
        bens_direitos=bens,
        doacoes_efetuadas=doacoes,
        pagamentos_efetuados=pagamentos,
        rendimentos_exclusivos=rend_exclusivos,
        rendimentos_isentos=rend_isentos,
        rendimentos_tributaveis_pj=rend_trib_pj,
        summary=resumo,
    )


# ────────────────────────────────────────────────────────────────────────────────
#  CLI helper
# ────────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, json

    ap = argparse.ArgumentParser(description="Parse IRPF-2025 XML → JSON")
    ap.add_argument("xmlfile", type=Path)
    args = ap.parse_args()

    decl = parse_irpf2025(args.xmlfile)
    print(json.dumps(decl.model_dump(mode="json"), indent=2, ensure_ascii=False))


