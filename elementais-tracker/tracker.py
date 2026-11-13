#!/usr/bin/env python3
"""
Rastreador de Elementais (Fortnite)

Vigia o ecrã enquanto jogas. Quando aparece a mensagem "NOVO - FOI PARA A COLEÇÃO"
com a imagem do elemental, reconhece qual é e guarda-o em elementais.json.
Depois importas esse ficheiro na página (botão "Importar do rastreador").

Uso:   python tracker.py                 (monitor principal)
       python tracker.py --monitor 2
       python tracker.py --imagem captura.png   (testa numa captura e sai)
Para parar: Ctrl+C
"""
import argparse, json, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import cv2
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(AQUI, "refs")
SAIDA = os.path.join(AQUI, "elementais.json")
TOTAL = 44
IGNORAR = {2}            # o Kelper não tem a variante Amaldiçoado
LIMIAR = 0.70            # confiança mínima (0 a 1)
MARGEM = 0.10            # o 1.º lugar tem de ganhar ao 2.º por pelo menos isto
ESCALA_BASE = 0.40       # tamanho do ícone numa captura com 2560 px de largura


def carregar_refs():
    refs = []
    for i in range(1, TOTAL + 1):
        if i in IGNORAR:
            continue
        img = cv2.imread(os.path.join(REFS, "%02d.png" % i), cv2.IMREAD_COLOR)
        msk = cv2.imread(os.path.join(REFS, "mask_%02d.png" % i), cv2.IMREAD_GRAYSCALE)
        if img is None or msk is None:
            sys.exit("Faltam ficheiros em refs/ (%02d)" % i)
        refs.append((i, img, msk))
    return refs


def aviso_visivel(frame):
    """True se a faixa escura com 'FOI PARA A COLEÇÃO' (texto branco) está no ecrã."""
    h, w = frame.shape[:2]
    for dy in (0, -.006, .006):                       # tolera pequenas diferenças de HUD/animação
        r = frame[int((.157 + dy) * h):int((.175 + dy) * h), int(.45 * w):int(.55 * w)]
        g = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)
        branco, escuro = (g > 200).mean(), (g < 80).mean()
        if 0.05 < branco < 0.6 and escuro > 0.22:
            return True
    return False


_CACHE = {}      # modelos já redimensionados/rodados (a resolução não muda durante o jogo)


def _modelo(i, img, msk, s, a):
    k = (i, round(s, 4), a)
    if k not in _CACHE:
        if len(_CACHE) > 20000:
            _CACHE.clear()
        t0 = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        m0 = cv2.resize(msk, (t0.shape[1], t0.shape[0]), interpolation=cv2.INTER_NEAREST)
        M = cv2.getRotationMatrix2D((t0.shape[1] / 2, t0.shape[0] / 2), a, 1)
        t = cv2.warpAffine(t0, M, (t0.shape[1], t0.shape[0]))
        m = cv2.warpAffine(m0, M, (t0.shape[1], t0.shape[0]))
        _CACHE[k] = (t, cv2.merge([m, m, m]))
    return _CACHE[k]


def pontuar(zona, refs, escalas, angulos):
    pts = {}
    for i, img, msk in refs:
        melhor = 0.0
        for s in escalas:
            if int(img.shape[0] * s) < 8 or int(img.shape[0] * s) >= zona.shape[0] or int(img.shape[1] * s) >= zona.shape[1]:
                continue
            for a in angulos:
                t, m = _modelo(i, img, msk, s, a)
                v = cv2.matchTemplate(zona, t, cv2.TM_CCOEFF_NORMED, mask=m).max()
                if v > melhor:
                    melhor = float(v)
        pts[i] = melhor
    return pts


def pontuacoes(frame, refs):
    """{id: pontuação} dos elementais para o aviso no ecrã (None se não há aviso)."""
    if not aviso_visivel(frame):
        return None
    h, w = frame.shape[:2]
    zona = frame[int(.085 * h):int(.185 * h), int(.465 * w):int(.535 * w)]
    s0 = ESCALA_BASE * w / 2560
    meia = cv2.resize(zona, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)       # 1.ª passagem a meia resolução (3x mais rápida)
    pts = pontuar(meia, refs, [s0 * .5 * k for k in (0.8, 0.95, 1.1)], (-20, -10, 0, 10, 20))
    top = sorted(pts, key=lambda k: -pts[k])[:3]
    fino = [r for r in refs if r[0] in top]
    pts.update(pontuar(zona, fino, [s0 * k for k in np.arange(0.72, 1.3, 0.08)], range(-20, 21, 5)))
    return pts


def decidir(pts):
    """(id, conf) se a pontuação de um só frame chega; senão None."""
    ordem = sorted(pts, key=lambda k: -pts[k])
    a, b = ordem[0], ordem[1]
    if pts[a] >= LIMIAR and pts[a] - pts[b] >= MARGEM:
        return a, pts[a]
    return None


def reconhecer(frame, refs):
    """Devolve (id, confianca) do elemental no aviso, ou None."""
    pts = pontuacoes(frame, refs)
    return decidir(pts) if pts else None


def guardar_falha(frame, pts):
    """Guarda a captura de um aviso que não foi reconhecido (pasta falhas/), para se poder afinar."""
    try:
        pasta = os.path.join(AQUI, "falhas")
        os.makedirs(pasta, exist_ok=True)
        top = sorted(pts, key=lambda k: -pts[k])[:2]
        nome = "%s_%02d-%.2f_%02d-%.2f.png" % (time.strftime("%Y%m%d-%H%M%S"), top[0], pts[top[0]], top[1], pts[top[1]])
        cv2.imwrite(os.path.join(pasta, nome), frame)
        antigos = sorted(os.listdir(pasta))[:-8]
        for f in antigos:
            os.remove(os.path.join(pasta, f))
        return nome
    except Exception:
        return None


def ler_estado():
    try:
        with open(SAIDA, encoding="utf-8") as f:
            return [int(x) for x in json.load(f).get("found", [])]
    except Exception:
        return []


def guardar(ordem):
    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump({"found": ordem, "last": ordem[-1] if ordem else None,
                   "updated": time.strftime("%Y-%m-%d %H:%M:%S")}, f)


import config
import perfis
CONFIG = config.CAMINHO
PORTA = 8765
ESTADO = {"obs": True, "pagina_visto": 0.0}      # a sobreposição OBS pode ser desligada (o resto do servidor continua)


def ler_config():
    return config.ler()


TIPOS = {".html": "text/html; charset=utf-8", ".png": "image/png", ".json": "application/json"}


class Servidor(BaseHTTPRequestHandler):
    """Serve a sobreposição (OBS) e o estado, só neste PC (localhost)."""

    def _cors(self):
        # permite que a página dos Elementais (noutro endereço) fale com este PC
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        rota = self.path.split("?")[0]
        if rota not in ("/estado", "/config", "/perfis"):
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            d = json.loads(self.rfile.read(min(n, 100000)).decode("utf-8"))
            if rota == "/perfis":                 # a página muda / cria / renomeia contas
                acao = d.get("acao")
                if acao == "trocar":
                    perfis.trocar(str(d.get("id")))
                elif acao == "novo":
                    pf = perfis.novo(str(d.get("nome") or "")[:24] or None)
                    perfis.trocar(pf["id"])
                elif acao == "renomear" and str(d.get("nome") or "").strip():
                    perfis.definir(str(d.get("id")), nome=str(d["nome"]).strip()[:24])
                self.send_response(200)
                self._cors()
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if rota == "/config":
                config.guardar(opacidade=float(d.get("opacidade", 0.6)))
                self.send_response(200)
                self._cors()
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            lista = []
            for x in d.get("found", []):
                x = int(x)
                if 1 <= x <= TOTAL and x not in IGNORAR and x not in lista:
                    lista.append(x)
            guardar(lista)
            self.send_response(200)
        except Exception:
            self.send_response(400)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/pagina":
            f = os.path.join(AQUI, "pagina.html")
        elif p in ("/", "/overlay"):
            if not ESTADO["obs"]:
                self.send_error(404, "Sobreposicao OBS desativada")
                return
            f = os.path.join(AQUI, "overlay.html")
        elif p == "/estado":
            if self.headers.get("Origin"):        # a página (noutro endereço) é que envia Origin
                ESTADO["pagina_visto"] = time.time()
            try:
                with open(SAIDA, encoding="utf-8") as fh:
                    d = json.load(fh)
            except Exception:
                d = {"found": [], "last": None}
            pf = perfis.ativo()
            d["perfil"], d["perfil_nome"] = pf["id"], pf["nome"]
            dados = json.dumps(d, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", TIPOS[".json"])
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            self.wfile.write(dados)
            return
        elif p == "/perfis":
            dados = json.dumps({"ativo": perfis.ativo()["id"],
                                "lista": [{"id": x["id"], "nome": x["nome"]} for x in perfis.lista()]},
                               ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", TIPOS[".json"])
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            self.wfile.write(dados)
            return
        elif p == "/config":
            dados = json.dumps(ler_config()).encode()
            self.send_response(200)
            self.send_header("Content-Type", TIPOS[".json"])
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            self.wfile.write(dados)
            return
        elif p.startswith("/refs/") and ".." not in p:
            f = os.path.join(AQUI, p.lstrip("/"))
        else:
            f = None
        if not f or not os.path.isfile(f):
            if p == "/estado":
                dados = b'{"found":[],"last":null}'
                self.send_response(200)
                self.send_header("Content-Type", TIPOS[".json"])
                self.send_header("Cache-Control", "no-store")
                self._cors()
                self.end_headers()
                self.wfile.write(dados)
                return
            self.send_error(404)
            return
        with open(f, "rb") as fh:
            dados = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", TIPOS.get(os.path.splitext(f)[1], "application/octet-stream"))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(dados)

    def log_message(self, *args):
        pass


def iniciar_servidor():
    try:
        s = ThreadingHTTPServer(("127.0.0.1", PORTA), Servidor)
    except OSError:
        print("Aviso: a porta %d está ocupada; a sobreposição OBS não ficou disponível." % PORTA)
        return
    threading.Thread(target=s.serve_forever, daemon=True).start()
    print("Sobreposição para o OBS: http://localhost:%d/overlay" % PORTA)


class Rastreio:
    """Lê o ecrã numa thread e guarda os elementais novos. Pode ser ligado e desligado à vontade."""

    def __init__(self, monitor=1, intervalo=0.4, aviso=print):
        self.monitor, self.intervalo, self.aviso = monitor, intervalo, aviso
        self._parar = threading.Event()
        self._thread = None
        self._refs = None

    @property
    def ativo(self):
        return self._thread is not None and self._thread.is_alive()

    def iniciar(self):
        if self.ativo:
            return
        self._parar.clear()
        self._thread = threading.Thread(target=self._correr, daemon=True)
        self._thread.start()

    def parar(self):
        self._parar.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._thread = None

    def _correr(self):
        try:
            import mss
            if self._refs is None:
                self._refs = carregar_refs()
            visto = 0.0
            votos, melhor_frame, sem_aviso = [], None, 0
            self.aviso("Rastreador ligado (monitor %d). Quando aparecer 'NOVO - FOI PARA A COLEÇÃO' "
                       "o elemental é guardado." % self.monitor)

            def aceitar(i, c):
                ordem = ler_estado()     # inclui o que foi marcado à mão na página
                if i not in ordem:
                    ordem.append(i)
                    guardar(ordem)
                    self.aviso("Novo elemental: n.º %02d (confiança %.2f)  total %d/%d"
                               % (i, c, len(ordem), TOTAL - len(IGNORAR)))
                else:
                    self.aviso("Elemental n.º %02d já estava guardado." % i)

            with mss.mss() as sct:
                mon = sct.monitors[self.monitor]
                while not self._parar.is_set():
                    frame = np.array(sct.grab(mon))[:, :, :3].copy()
                    espera = self.intervalo
                    pts = pontuacoes(frame, self._refs) if time.time() - visto > 6 else None
                    if pts:
                        sem_aviso = 0
                        espera = min(espera, 0.15)          # o aviso dura pouco: lê mais depressa
                        r = decidir(pts)
                        if r:
                            visto = time.time()      # o aviso dura uns segundos: conta uma só vez
                            aceitar(*r)
                            votos, melhor_frame = [], None
                        else:
                            ordem = sorted(pts, key=lambda k: -pts[k])
                            votos.append((ordem[0], pts[ordem[0]], pts[ordem[0]] - pts[ordem[1]]))
                            if melhor_frame is None or pts[ordem[0]] > melhor_frame[1][ordem[0]]:
                                melhor_frame = (frame, pts)
                            # vários frames a apontar para o mesmo elemental, mesmo com pouca margem, chegam
                            ids = [v[0] for v in votos]
                            lider = max(set(ids), key=ids.count)
                            sc = [v[1] for v in votos if v[0] == lider]
                            mg = [v[2] for v in votos if v[0] == lider]
                            if (len(sc) >= 3 and ids.count(lider) >= 0.7 * len(ids)
                                    and sum(sc) / len(sc) >= 0.60 and sum(mg) / len(mg) >= 0.04):
                                visto = time.time()
                                aceitar(lider, max(sc))
                                votos, melhor_frame = [], None
                    elif votos:
                        sem_aviso += 1
                        if sem_aviso >= 4:                  # o aviso desapareceu sem ser reconhecido
                            nome = guardar_falha(*melhor_frame) if melhor_frame else None
                            self.aviso("Vi o aviso de novo elemental mas não o reconheci. Marca-o à mão em Coleção%s."
                                       % (" (captura em falhas/%s)" % nome if nome else ""))
                            votos, melhor_frame = [], None
                    self._parar.wait(espera)
        except Exception as e:
            self.aviso("Erro no rastreador: %s" % e)
        finally:
            self.aviso("Rastreador desligado.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=1)
    ap.add_argument("--intervalo", type=float, default=0.4)
    ap.add_argument("--imagem")
    a = ap.parse_args()
    if a.imagem:
        refs = carregar_refs()
        frame = cv2.imread(a.imagem, cv2.IMREAD_COLOR)
        print("Aviso visível:", aviso_visivel(frame))
        print("Resultado:", reconhecer(frame, refs))
        return
    iniciar_servidor()
    r = Rastreio(a.monitor, a.intervalo)
    r.iniciar()
    print("(Ctrl+C para parar)")
    while r.ativo:
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nParado.")
