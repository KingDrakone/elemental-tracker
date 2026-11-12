"""
Perfis (uma coleção por conta do Fortnite/Epic neste PC).

O ficheiro elementais.json é sempre a coleção do perfil ATIVO (é o que o rastreador, a página e os
overlays leem). Cada perfil guarda a sua cópia em perfis/<id>.json; ao trocar de perfil a coleção
ativa é guardada e a do outro perfil é carregada.

Deteção automática da conta (melhor esforço): lê o fim de FortniteGame.log e vê qual é o id de
conta (32 caracteres hexadecimais) que mais aparece. Se não funcionar no teu PC, usa
"Mudar de perfil" no painel (manual).
"""
import glob
import json
import os
import re
import threading
import time
from collections import Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "perfis")
INDICE = os.path.join(AQUI, "perfis.json")
ATIVO_JSON = os.path.join(AQUI, "elementais.json")
_trava = threading.RLock()
ID_RE = re.compile(r"(?<![0-9a-fA-F])([0-9a-f]{32})(?![0-9a-fA-F])")


def _ler(caminho, padrao):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return padrao


def _escrever(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)


def indice():
    """{'ativo': id, 'lista': [{'id','nome','conta'}]} — cria o perfil inicial se ainda não existir."""
    with _trava:
        d = _ler(INDICE, None)
        if not isinstance(d, dict) or not d.get("lista"):
            d = {"ativo": "p1", "lista": [{"id": "p1", "nome": "Principal", "conta": ""}]}
            _escrever(INDICE, d)
        if d.get("ativo") not in [p["id"] for p in d["lista"]]:
            d["ativo"] = d["lista"][0]["id"]
            _escrever(INDICE, d)
        return d


def ativo():
    d = indice()
    return next(p for p in d["lista"] if p["id"] == d["ativo"])


def lista():
    return indice()["lista"]


def _ficheiro(pid):
    return os.path.join(PASTA, pid + ".json")


def trocar(pid):
    """Guarda a coleção do perfil ativo e carrega a do perfil `pid`. Devolve o perfil, ou None."""
    with _trava:
        d = indice()
        alvo = next((p for p in d["lista"] if p["id"] == pid), None)
        if alvo is None or pid == d["ativo"]:
            return alvo
        atual = _ler(ATIVO_JSON, {"found": [], "last": None})
        _escrever(_ficheiro(d["ativo"]), atual)
        novo = _ler(_ficheiro(pid), {"found": [], "last": None})
        _escrever(ATIVO_JSON, novo)
        d["ativo"] = pid
        _escrever(INDICE, d)
        return alvo


def proximo():
    """Passa ao perfil seguinte (manual)."""
    d = indice()
    ids = [p["id"] for p in d["lista"]]
    return trocar(ids[(ids.index(d["ativo"]) + 1) % len(ids)])


def novo(nome=None, conta=""):
    with _trava:
        d = indice()
        n = 1
        while any(p["id"] == "p%d" % n for p in d["lista"]):
            n += 1
        p = {"id": "p%d" % n, "nome": nome or "Perfil %d" % (len(d["lista"]) + 1), "conta": conta}
        d["lista"].append(p)
        _escrever(INDICE, d)
        return p


def definir(pid, **campos):
    with _trava:
        d = indice()
        for p in d["lista"]:
            if p["id"] == pid:
                p.update(campos)
        _escrever(INDICE, d)


# ------------------------------------------------------------ deteção da conta
def pasta_logs():
    base = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(base, "FortniteGame", "Saved", "Logs") if base else ""


def _fim_do_ficheiro(caminho, n=2_000_000):
    with open(caminho, "rb") as f:
        f.seek(0, os.SEEK_END)
        tam = f.tell()
        f.seek(max(0, tam - n))
        return f.read().decode("utf-8", "ignore")


def candidatos(pasta=None):
    """Os ids de conta que aparecem no log, do mais frequente para o menos: [(id, vezes)]."""
    pasta = pasta or pasta_logs()
    ficheiros = []
    if pasta and os.path.isdir(pasta):
        principal = os.path.join(pasta, "FortniteGame.log")
        if os.path.isfile(principal):
            ficheiros.append(principal)
    cont = Counter()
    for f in ficheiros:
        try:
            cont.update(ID_RE.findall(_fim_do_ficheiro(f)))
        except Exception:
            pass
    return cont.most_common(5)


def detetar(pasta=None):
    """(id_da_conta, nome_ou_None) da conta com sessão iniciada, ou None se não der certeza."""
    c = candidatos(pasta)
    if not c or c[0][1] < 3:
        return None
    if len(c) > 1 and c[0][1] < 2 * c[1][1]:      # sem um vencedor claro: não arrisca
        return None
    conta = c[0][0]
    nome = None
    pasta = pasta or pasta_logs()
    try:
        txt = _fim_do_ficheiro(os.path.join(pasta, "FortniteGame.log"))
        m = re.search(r"(?i)display ?name\W{1,4}([A-Za-z0-9_.\- ]{3,16})", txt)
        if m:
            nome = m.group(1).strip()
    except Exception:
        pass
    return conta, nome


def aplicar_conta(conta, nome=None):
    """Liga a conta detetada a um perfil JÁ EXISTENTE e troca para ele. Nunca cria perfis sozinho
    (os ids do log mudam e criavam perfis aleatórios). Devolve (perfil, mudou, conta_desconhecida)."""
    with _trava:
        d = indice()
        p = next((x for x in d["lista"] if x.get("conta") == conta), None)
        if p is None:
            livre = next((x for x in d["lista"] if not x.get("conta")), None)
            if livre is not None and len(d["lista"]) == 1:     # primeira conta vista: adota o perfil inicial
                livre["conta"] = conta
                if nome:
                    livre["nome"] = nome
                _escrever(INDICE, d)
                p = livre
            else:
                return ativo(), False, True
        elif nome and (p["nome"] == "Principal" or p["nome"].startswith(("Perfil ", "Conta "))):
            definir(p["id"], nome=nome)
        antes = indice()["ativo"]
        trocar(p["id"])
        return ativo(), antes != p["id"], False


def limpar_automaticos():
    """Remove os perfis 'Conta xxxxxx' vazios que versões anteriores criaram sozinhas. Devolve quantos."""
    with _trava:
        d = indice()
        n = 0
        for p in list(d["lista"]):
            if p["id"] == d["ativo"] or not p["nome"].startswith("Conta "):
                continue
            col = _ler(_ficheiro(p["id"]), {"found": []})
            if not col.get("found"):
                d["lista"].remove(p)
                n += 1
                try:
                    os.remove(_ficheiro(p["id"]))
                except OSError:
                    pass
        if n:
            _escrever(INDICE, d)
        return n
