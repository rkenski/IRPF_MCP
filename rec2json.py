import json

# Mapas com layout de cada tipo de registro (colunas: nome, início, fim)
LAYOUTS = {
    "HC": [
        ("TP_REG", 0, 2),
        ("NR_CPF_CNPJ", 2, 13),
        ("FILLER", 13, 16),
        ("NR_CONTROLE", 16, 26),
    ],
    "RC": [
        ("TP_REG", 0, 2),
        ("NR_CPF_CNPJ", 2, 13),
        ("FILLER1", 13, 16),
        ("DIAREC", 16, 18),
        ("MESREC", 18, 20),
        ("ANOREC", 20, 24),
        ("HORAREC", 24, 26),
        ("MINREC", 26, 28),
        ("SEGREC", 28, 30),
        ("LOCALREC", 30, 55),
        ("NR_REMESSA", 55, 59),
        ("ASSINATURA", 59, 69),
        ("IN_GATEWAY", 69, 70),
        ("FILLER2", 70, 71),
        ("IN_APLIC_TRANSMISSAO", 71, 72),
        ("APLIC_TRANSMISSAO", 72, 74),
        ("COD_AG_TRANSMISSOR", 74, 77),
        ("NI_ASSINATURA_DECL", 77, 91),
        ("CONTROLE_SRF", 91, 101),
        ("FILLER3", 101, 121),
        ("NR_CONTROLE", 121, 131),
    ],
    "NC": [
        ("TP_REG", 0, 2),
        ("IN_ACAO_FISCAL", 2, 3),
        ("NM_DELEGADO", 3, 63),
        ("NR_MATRIC_DELEGADO", 63, 71),
        ("NR_CARGO", 71, 72),
        ("NR_UA", 72, 79),
        ("NM_UA", 79, 129),
        ("DT_VENCIMENTO", 129, 137),
        ("QT_MESES", 137, 139),
        ("VR_MULTA", 139, 152),
        ("NR_DISTRIBUICAO", 152, 166),
        ("IN_OBRIGATORIEDADE", 166, 167),
        ("TP_DELEGACIA", 167, 224),
        ("FILLER", 224, 252),
        ("NR_CONTROLE", 252, 262),
    ],
    "VC": [
        ("TP_REG", 0, 2),
        ("IN_PENDENCIA", 2, 7),
        ("QTD_RETIFICADORAS", 7, 10),
        ("IN_DEBITO", 10, 11),
        ("DATA_MENSAGEM", 11, 19),
        ("IN_SALDO_RESTITUICAO", 19, 20),
        ("DATA_SALDO_RESTITUICAO", 20, 28),
        ("NR_CPF_DARF1", 28, 39),
        ("VL_DARF1", 39, 52),
        ("NR_CPF_DARF2", 52, 63),
        ("VL_DARF2", 63, 76),
        ("NR_CPF_DARF3", 76, 87),
        ("VL_DARF3", 87, 100),
        ("NR_CPF_DARF4", 100, 111),
        ("VL_DARF4", 111, 124),
        ("NR_CPF_DARF5", 124, 135),
        ("VL_DARF5", 135, 148),
        ("NR_CPF_DARF6", 148, 159),
        ("VL_DARF6", 159, 172),
        ("NR_CPF_DARF7", 172, 183),
        ("VL_DARF7", 183, 196),
        ("NR_CONTROLE", 196, 206),
    ],
    "TC": [
        ("TP_REG", 0, 2),
        ("NR_CPF_CNPJ", 2, 13),
        ("FILLER", 13, 16),
        ("SIGNET", 16, 48),
        ("NR_CONTROLE", 48, 58),
    ]
}

def parse_line(line):
    reg_type = line[:2]
    layout = LAYOUTS.get(reg_type)
    if not layout:
        # Assume MC (mensagem) se não for outro conhecido
        if reg_type == "MC":
            return {
                "TP_REG": "MC",
                "DES_MENSAGEM": line[2:-10].strip(),
                "NR_CONTROLE": line[-10:]
            }
        return {"TP_REG": "UNKNOWN", "RAW": line.strip()}
    
    parsed = {}
    for field, start, end in layout:
        parsed[field] = line[start:end].strip()
    return parsed

def parse_rec_file(file_path):
    data = {
        "HC": {},
        "RC": {},
        "NC": [],
        "VC": {},
        "MC": [],
        "TC": {},
        "UNKNOWN": []
    }

    with open(file_path, "r", encoding="latin-1") as f:
        for line in f:
            record = parse_line(line.rstrip("\r\n"))
            kind = record.get("TP_REG", "UNKNOWN")
            if kind == "HC":
                data["HC"] = record
            elif kind == "RC":
                data["RC"] = record
            elif kind == "NC":
                data["NC"].append(record)
            elif kind == "VC":
                data["VC"] = record
            elif kind == "MC":
                data["MC"].append(record)
            elif kind == "TC":
                data["TC"] = record
            else:
                data["UNKNOWN"].append(record)
    return data

# Exemplo de uso:
if __name__ == "__main__":
    import sys
    path = sys.argv[1]  # Exemplo: python script.py recibo.rec
    result = parse_rec_file(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


file = '/home/kenski/projects/IRPF/30390505838-IRPF-A-2023-2022-ORIGI.DEC'

result = parse_rec_file(file)
