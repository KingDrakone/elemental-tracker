"""Definições partilhadas (guardadas em config.json): painel, sobreposições e página."""
import json, os

CAMINHO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
PADRAO = {
    "opacidade": 0.6,        # 0.1 a 1 (a página também a muda)
    "tamanho": 100,          # % do overlay do jogo
    "idioma": "pt",          # pt | en  (overlays)
    "overlay_jogo": True,
    "estilo": "completo",    # completo (grelha + cartão) | simples (só contador + cartão)
    "rastreio": True,
    "obs": True,
    "monitor": 1,
    "x": 20,
    "y": 140,
    "abrir_pagina": False,   # abrir a página numa janela ao iniciar o painel
    "auto_perfil": True,     # troca de perfil sozinho quando mudas de conta no Fortnite
    "bloqueado": True,       # True: os cliques passam para o jogo; False: podes arrastar o overlay
}


def _limpa(c):
    c["opacidade"] = min(1.0, max(0.1, float(c["opacidade"])))
    c["tamanho"] = int(min(200, max(50, int(c["tamanho"]))))
    c["idioma"] = c["idioma"] if c["idioma"] in ("pt", "en") else "pt"
    c["estilo"] = c["estilo"] if c["estilo"] in ("completo", "simples") else "completo"
    c["monitor"] = max(1, int(c["monitor"]))
    c["x"], c["y"] = int(c["x"]), int(c["y"])
    for k in ("overlay_jogo", "rastreio", "obs", "bloqueado", "auto_perfil", "abrir_pagina"):
        c[k] = bool(c[k])
    return c


def ler():
    c = dict(PADRAO)
    try:
        with open(CAMINHO, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            c.update({k: v for k, v in d.items() if k in PADRAO})
    except Exception:
        pass
    try:
        return _limpa(c)
    except Exception:
        return dict(PADRAO)


def guardar(**novos):
    c = ler()
    c.update({k: v for k, v in novos.items() if k in PADRAO})
    c = _limpa(c)
    try:
        with open(CAMINHO, "w", encoding="utf-8") as f:
            json.dump(c, f, indent=1)
    except Exception:
        pass
    return c
