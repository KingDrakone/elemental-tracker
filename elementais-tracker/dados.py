"""Dados dos elementais (nomes, números, raridades), partilhados pelo painel e pela sobreposição."""
VN_PT = ["Normal", "Valioso", "Amaldiçoado", "Dourado"]
VN_EN = ["Normal", "Fortune", "Cursed", "Gold"]
RN_EN = {"Raro": "Rare", "Épico": "Epic", "Lendário": "Legendary", "Mítico": "Mythic"}
NUM = {32: 1, 30: 2, 31: 3, 26: 5, 24: 6, 25: 7, 23: 9, 21: 10, 22: 11, 20: 13, 18: 14, 19: 15, 15: 17, 13: 18, 14: 19, 2: 21, 0: 22, 1: 23, 5: 25, 3: 26, 4: 27, 12: 29, 10: 30, 11: 31, 34: 37, 16: 38, 17: 39, 9: 41, 7: 42, 8: 43, 29: 49, 27: 50, 28: 51, 33: 57, 6: 58, 35: 53, 36: 54, 37: 55, 38: 33, 39: 34, 40: 35, 41: 45, 42: 46, 43: 47, 44: 4, 45: 36, 46: 8, 47: 12, 48: 16, 49: 20, 50: 32, 51: 44, 52: 28, 53: 24, 54: 40, 55: 56, 56: 48, 57: 52}
PT = {"Squiplash": 'Mô Lusco', "Halfpeel'd": 'Descascadinho', 'Re-Pete': 'Repetácio', "Barry O'Fish": 'Barrilson', 'Wayfinder': 'Localizador', 'Chester': 'Baunardo', 'Exmarks': 'Xisconde', 'Kelper': 'Apatilda', "Lil' Squibbly": 'Polvitozinho', "Lil' Flacko": 'Flacko Jr.', "Lil' Uzi Vert Jr.": "Lil' Uzi Vert Jr.", 'Transponder Snail': 'Caracol Telepático', 'Doces Sonhos': 'Bons Sonhos', 'Plundarrgh': 'Moedonho', 'Mini Miku': 'Mini Miku', 'Mô Lusco': 'Mô Lusco', 'Oscar II': 'Oscar II'}
VN = VN_PT
CORES = {"Raro": "#4d9bff", "Épico": "#b565ff", "Lendário": "#ffb02e", "Mítico": "#ff5a5a"}
RARS = [
    ("Raro", [("Halfpeel'd", [32, 30, 31, 44]), ("Re-Pete", [26, 24, 25, 46]), ("Barry O'Fish", [23, 21, 22, 47]), ("Wayfinder", [20, 18, 19, 48])]),
    ("Épico", [("Chester", [15, 13, 14, 49]), ("Exmarks", [5, 3, 4, 52]), ("Kelper", [2, 0, 1, 53]), ("Lil' Squibbly", [12, 10, 11, 50])]),
    ("Lendário", [("Lil' Flacko", [34, 16, 17, 54]), ("Lil' Uzi Vert Jr.", [9, 7, 8, 51]), ("Transponder Snail", [33]), ("Squiplash", [38, 39, 40, 45]), ("Oscar II", [41, 42, 43, 56])]),
    ("Mítico", [("Doces Sonhos", [6]), ("Plundarrgh", [29, 27, 28, 57]), ("Mini Miku", [35, 36, 37, 55])]),
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
