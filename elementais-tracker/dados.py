"""Dados dos elementais (nomes, números, raridades), partilhados pelo painel e pela sobreposição."""
VN_PT = ["Normal", "Valioso", "Amaldiçoado"]
VN_EN = ["Normal", "Fortune", "Cursed"]
RN_EN = {"Raro": "Rare", "Épico": "Epic", "Lendário": "Legendary", "Mítico": "Mythic"}
NUM = {32: 1, 30: 2, 31: 3, 26: 5, 24: 6, 25: 7, 23: 9, 21: 10, 22: 11, 20: 13, 18: 14, 19: 15, 15: 17, 13: 18, 14: 19, 2: 21, 0: 22, 5: 25, 3: 26, 4: 27, 12: 29, 10: 30, 11: 31, 34: 37, 16: 38, 17: 39, 9: 41, 7: 42, 8: 43, 29: 49, 27: 50, 28: 51, 33: 57, 6: 58}
PT = {"Halfpeel'd": 'Descascadinho', 'Re-Pete': 'Repetácio', "Barry O'Fish": 'Barrilson', 'Wayfinder': 'Localizador', 'Chester': 'Baunardo', 'Exmarks': 'Xisconde', 'Kelper': 'Apatilda', "Lil' Squibbly": 'Polvitozinho', "Lil' Flacko": 'Flacko Jr.', "Lil' Uzi Vert Jr.": "Lil' Uzi Vert Jr.", 'Transponder Snail': 'Caracol Telepático', 'Doces Sonhos': 'Bons Sonhos', 'Plundarrgh': 'Moedonho'}
VN = VN_PT
CORES = {"Raro": "#4d9bff", "Épico": "#b565ff", "Lendário": "#ffb02e", "Mítico": "#ff5a5a"}
RARS = [
    ("Raro", [("Halfpeel'd", [32, 30, 31]), ("Re-Pete", [26, 24, 25]), ("Barry O'Fish", [23, 21, 22]), ("Wayfinder", [20, 18, 19])]),
    ("Épico", [("Chester", [15, 13, 14]), ("Exmarks", [5, 3, 4]), ("Kelper", [2, 0]), ("Lil' Squibbly", [12, 10, 11])]),
    ("Lendário", [("Lil' Flacko", [34, 16, 17]), ("Lil' Uzi Vert Jr.", [9, 7, 8]), ("Transponder Snail", [33])]),
    ("Mítico", [("Doces Sonhos", [6]), ("Plundarrgh", [29, 27, 28])]),
]
INFO = {}
for rar, grupos in RARS:
    for nome, idx in grupos:
        for k, i in enumerate(idx):
            INFO[i] = (nome, k, rar)
TOTAL = len(INFO)
ORDEM = [i for _, grupos in RARS for _, idx in grupos for i in idx]   # ordem da grelha


def nome_l(n, en=False):
    """Nome do elemental no idioma pedido (n é o nome em inglês do jogo)."""
    if n == "Doces Sonhos":
        return "Sweet Dreams" if en else "Bons Sonhos"
    return n if en else PT.get(n, n)


def descricao(i, en=False):
    """'#57 Caracol Telepático (Normal)' para o índice i (0-based)."""
    n, k, r = INFO[i]
    vn = VN_EN if en else VN_PT
    return "%s%s (%s)" % ("#%d " % NUM[i] if i in NUM else "", nome_l(n, en), vn[k])
