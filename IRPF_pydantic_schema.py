from typing import Optional, List
from pydantic import BaseModel

# --- Direct children classes ---

class Alimentandos(BaseModel):
    confirmacao: Optional[str]
    tipoItens: Optional[str]

class AtividadeRural(BaseModel):
    ultimoIndiceGerado: Optional[str]

class Bens(BaseModel):
    bensSemMarcacaoBemInventariar: Optional[str]
    bensSemValorDummy: Optional[str]
    existeAtualizacaoValorBem: Optional[int]
    numeroProcessoAtualizacaoValorBem: Optional[str]
    tipoItens: Optional[str]
    totalExercicioAnterior: Optional[str]
    totalExercicioAtual: Optional[str]
    totalItens: Optional[int]
    ultimoIndiceGerado: Optional[int]

class ColecaoEstatutoCriancaAdolescente(BaseModel):
    tipoItens: Optional[str]
    totalDeducaoIncentivoBruto: Optional[str]
    totalDeducaoIncentivoLiquido: Optional[str]

class ColecaoEstatutoIdoso(BaseModel):
    tipoItens: Optional[str]
    totalDeducaoIncentivoBruto: Optional[str]
    totalDeducaoIncentivoLiquido: Optional[str]

class Comparativo(BaseModel):
    baseCalcCompleta: Optional[str]
    baseCalcSimplificada: Optional[str]
    impRestituirCompleta: Optional[str]
    impRestituirSimplificada: Optional[str]
    saldoPagarCompleta: Optional[str]
    saldoPagarSimplificada: Optional[str]
    totalRendTribCompleta: Optional[str]
    totalRendTribSimplificada: Optional[str]

class Contribuinte(BaseModel):
    bairro: Optional[str]
    bairroExt: Optional[str]
    baseCalculoFinalLei14754: Optional[str]
    celular: Optional[int]
    cep: Optional[str]
    cepExt: Optional[str]
    cidade: Optional[str]
    codigoExterior: Optional[str]
    complemento: Optional[str]
    complementoExt: Optional[str]
    conjuge: Optional[int]
    cpfConjuge: Optional[str]
    cpfProcurador: Optional[str]
    dataNascimento: Optional[str]
    dataRetorno: Optional[str]
    ddd: Optional[str]
    dddCelular: Optional[int]
    ddi: Optional[str]
    deficiente: Optional[str]
    email: Optional[str]
    exterior: Optional[int]
    impostoDevidoLei14754: Optional[str]
    logradouro: Optional[str]
    logradouroExt: Optional[str]
    municipio: Optional[int]
    naturezaOcupacao: Optional[int]
    nomePais: Optional[str]
    numero: Optional[int]
    numeroExt: Optional[str]
    ocupacaoPrincipal: Optional[int]
    pais: Optional[int]
    prejuizoAnoAnteriorLei14754: Optional[str]
    processoDigital: Optional[str]
    registroProfissional: Optional[str]
    retornoPais: Optional[str]
    telefone: Optional[str]
    telefoneExt: Optional[str]
    tipoLogradouro: Optional[str]
    tituloEleitor: Optional[str]
    uf: Optional[str]

class CopiaIdentificador(BaseModel):
    cpf: Optional[str]
    dataCriacao: Optional[str]
    dataUltimoAcesso: Optional[str]
    declaracaoRetificadora: Optional[int]
    enderecoDiferente: Optional[str]
    exercicio: Optional[int]
    inCLWeb: Optional[str]
    inNovaDeclaracao: Optional[int]
    inUtilizouAPP: Optional[int]
    inUtilizouAssistidaFontePagadora: Optional[int]
    inUtilizouAssistidaPlanoSaude: Optional[int]
    inUtilizouOnLine: Optional[int]
    inUtilizouPGD: Optional[int]
    inUtilizouRascunho: Optional[int]
    inUtilizouSalvarRecuperarOnLine: Optional[int]
    nome: Optional[str]
    numReciboDecRetif: Optional[str]
    numReciboTransmitido: Optional[int]
    numeroReciboDecAnterior: Optional[int]
    prepreenchida: Optional[int]
    resultadoDeclaracao: Optional[str]
    tipoDeclaracao: Optional[int]
    tipoDeclaracaoAES: Optional[str]
    tpIniciada: Optional[int]
    tpTransmitida: Optional[str]
    transmitida: Optional[int]
    versaoBeta: Optional[str]

class DependentesItem(BaseModel):
    codigo: Optional[str]
    cpfDependente: Optional[str]
    dataNascimento: Optional[str]
    ddd: Optional[str]
    dummy: Optional[str]
    email: Optional[str]
    indMoraComTitular: Optional[int]
    indSaidaPaisMesmaData: Optional[str]
    nome: Optional[str]
    telefone: Optional[str]

class Dependentes(BaseModel):
    tipoItens: Optional[str]
    item: Optional[List[DependentesItem]]

# Detailed placeholders
class Dividas(BaseModel):
    tipoItens: Optional[str]
    totalExercicioAnterior: Optional[str]
    totalExercicioAtual: Optional[str]
    totalPgtoAnual: Optional[str]
    ultimoIndiceGerado: Optional[str]

class Doacoes(BaseModel):
    tipoItens: Optional[str]
    totalDeducaoIncentivo: Optional[str]
    ultimoIndiceGerado: Optional[str]

class DoacoesEleitorais(BaseModel):
    tipoItens: Optional[str]
    totalDoacoes: Optional[str]

class Espolio(BaseModel):
    anoObito: Optional[str]
    cpfInventariante: Optional[str]
    indicadorBensInventariar: Optional[str]
    indicadorFinalEspolio: Optional[str]
    indicadorSobrepartilha: Optional[str]
    nomeInventariante: Optional[str]

class FundosInvestimentos(BaseModel):
    totalBaseCalcImposto: Optional[str]
    totalImpostoDevido: Optional[str]
    totalImpostoPago: Optional[str]
    totalImpostoRetidoFonteLei11033: Optional[str]

class FundosInvestimentosDependente(BaseModel):
    tipoItens: Optional[str]
    totalBaseCalculo: Optional[str]
    totalImpostoDevido: Optional[str]
    totalImpostoPago: Optional[str]
    totalImpostoRetidoFonteLei11033: Optional[str]

class Gcap(BaseModel):
    pass  # Nested structures are complex and can be added as needed

class Herdeiros(BaseModel):
    tipoItens: Optional[str]

class ImpostoPago(BaseModel):
    carneLeaoDependentes: Optional[str]
    carneLeaoTitular: Optional[str]
    impostoComplementar: Optional[str]
    impostoDevidoComRendExterior: Optional[str]
    impostoDevidoSemRendExterior: Optional[str]
    impostoPagoExterior: Optional[str]
    impostoRetidoFonte: Optional[str]
    impostoRetidoFonteDependentes: Optional[str]
    impostoRetidoFonteTitular: Optional[str]
    limiteImpPagoExterior: Optional[str]

class Pagamentos(BaseModel):
    tipoItens: Optional[str]
    totalContribEmpregadoDomestico: Optional[str]
    totalContribuicaoFunpresp: Optional[str]
    totalContribuicaoPreviPrivada: Optional[str]
    totalDeducoesInstrucao: Optional[str]
    totalDespesasMedicas: Optional[str]
    totalPensao: Optional[str]
    totalPensaoCartoral: Optional[str]
    ultimoIndiceGerado: Optional[int]

class RendAcm(BaseModel):
    totalRendRecebAcumuladamente: Optional[str]

class RendIsentos(BaseModel):
    total: Optional[str]

class RendPFDependente(BaseModel):
    tipoItens: Optional[str]
    totalAlugueis: Optional[str]
    totalDarfPago: Optional[str]
    totalDependentes: Optional[str]
    totalExterior: Optional[str]
    totalImpostoPagoExteriorCompensar: Optional[str]
    totalLivroCaixa: Optional[str]
    totalOutros: Optional[str]
    totalPensao: Optional[str]
    totalPessoaFisica: Optional[str]
    totalPrevidencia: Optional[str]
    usouImportacaoCarneLeaoWeb: Optional[str]

class RendPFTitular(BaseModel):
    NITPISPASEP: Optional[str]
    totalAlugueis: Optional[str]
    totalDarfPago: Optional[str]
    totalDependentes: Optional[str]
    totalExterior: Optional[str]
    totalImpostoPagoExteriorCompensar: Optional[str]
    totalLivroCaixa: Optional[str]
    totalNumDependentes: Optional[str]
    totalOutros: Optional[str]
    totalPensao: Optional[str]
    totalPessoaFisica: Optional[str]
    totalPrevidencia: Optional[str]
    usouImportacaoCarneLeaoWeb: Optional[str]

class RendPJ(BaseModel):
    totalRendRecebPessoaJuridica: Optional[str]

class RendPJComExigibilidade(BaseModel):
    pass

class RendTributacaoExclusiva(BaseModel):
    decimoTerceiro: Optional[str]
    decimoTerceiroDependentes: Optional[str]
    ganhosCapital: Optional[str]
    ganhosCapitalEmEspecie: Optional[str]
    ganhosCapitalEstrangeira: Optional[str]
    ganhosRendaVariavel: Optional[str]
    jurosCapitalProprio: Optional[str]
    lei14754: Optional[str]
    outros: Optional[str]
    participacaoLucrosResultados: Optional[str]
    rendAplicacoes: Optional[str]
    rraDependentes: Optional[str]
    rraTitular: Optional[str]
    total: Optional[str]

class RendaVariavel(BaseModel):
    totalBaseCalculo: Optional[str]
    totalIRFonteDayTrade: Optional[str]
    totalImpostoAPagar: Optional[str]
    totalImpostoPago: Optional[str]
    totalImpostoRetidoFonteLei11033: Optional[str]

class RendaVariavelDependente(BaseModel):
    pass

class RendimentosAplicacoesFinanceiras(BaseModel):
    pass

class Resumo(BaseModel):
    pass

class Saida(BaseModel):
    pass

# --- Classe model ---

class Classe(BaseModel):
    classeJava: Optional[str]
    dataHoraSalvamento: Optional[str]
    utlimoCPFAutenticado: Optional[str]
    alimentandos: Optional[Alimentandos]
    atividadeRural: Optional[AtividadeRural]
    bens: Optional[Bens]
    colecaoEstatutoCriancaAdolescente: Optional[ColecaoEstatutoCriancaAdolescente]
    colecaoEstatutoIdoso: Optional[ColecaoEstatutoIdoso]
    comparativo: Optional[Comparativo]
    contribuinte: Optional[Contribuinte]
    copiaIdentificador: Optional[CopiaIdentificador]
    dependentes: Optional[Dependentes]
    dividas: Optional[Dividas]
    doacoes: Optional[Doacoes]
    doacoesEleitorais: Optional[DoacoesEleitorais]
    espolio: Optional[Espolio]
    fundosInvestimentos: Optional[FundosInvestimentos]
    fundosInvestimentosDependente: Optional[FundosInvestimentosDependente]
    gcap: Optional[Gcap]
    herdeiros: Optional[Herdeiros]
    impostoPago: Optional[ImpostoPago]
    pagamentos: Optional[Pagamentos]
    rendAcm: Optional[RendAcm]
    rendIsentos: Optional[RendIsentos]
    rendPFDependente: Optional[RendPFDependente]
    rendPFTitular: Optional[RendPFTitular]
    rendPJ: Optional[RendPJ]
    rendPJComExigibilidade: Optional[RendPJComExigibilidade]
    rendTributacaoExclusiva: Optional[RendTributacaoExclusiva]
    rendaVariavel: Optional[RendaVariavel]
    rendaVariavelDependente: Optional[RendaVariavelDependente]
    rendimentosAplicacoesFinanceiras: Optional[RendimentosAplicacoesFinanceiras]
    resumo: Optional[Resumo]
    saida: Optional[Saida]
