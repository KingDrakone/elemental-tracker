#!/usr/bin/env python3
"""
Sobreposição sobre o ecrã do jogo (Fortnite em "Ecrã inteiro em janela").

Mostra por cima do jogo o contador de elementais e, quando apanhas um novo, um cartão
com a imagem e o nome durante 8 segundos. Lê o elementais.json que o tracker.py escreve,
por isso corre os dois ao mesmo tempo (duas janelas do Prompt de Comando):
    python tracker.py
    python sobreposicao.py

Opções:  --x 20 --y 140     posição no ecrã (pixeis, a partir do canto superior esquerdo)
         --tamanho 1.5      aumenta tudo
Fechar: Ctrl+C na janela do Prompt de Comando.
"""
import argparse, json, os, sys, time
import tkinter as tk

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "elementais.json")
REFS = os.path.join(AQUI, "refs")
from dados import (VN_PT, VN_EN, RN_EN, NUM, PT, CORES, RARS, INFO, TOTAL, ORDEM, nome_l as _nome_l)
import config
import perfis
FUNDO, PAINEL, TXT = "#010101", "#0a0e22", "#ffffff"   # #010101 fica transparente no Windows


def ler_opacidade():
    """Transparência escolhida (painel ou página), guardada em config.json."""
    return config.ler()["opacidade"]


def ler():
    try:
        with open(SAIDA, encoding="utf-8") as f:
            d = json.load(f)
        return [int(n) - 1 for n in d.get("found", []) if int(n) - 1 in INFO]
    except Exception:
        return []


def clique_atraves(janela, ativo=True):
    """No Windows, deixa (ativo) ou não os cliques passarem para o jogo."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        janela.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(janela.winfo_id())
        est = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        novo = (est | 0x80000 | 0x20) if ativo else ((est | 0x80000) & ~0x20)    # LAYERED | TRANSPARENT
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, novo)
    except Exception:
        pass


class Sobreposicao:
    def __init__(self, raiz, ao_mover=None):
        self.raiz = raiz
        self.vivo = True
        self.bloqueado = True
        self.ao_mover = ao_mover      # chamada com (x, y) quando largas o overlay depois de o arrastares
        self.dica = None
        self.antes = None
        self._p = (0, 0)

    def mostrar(self, sim):
        try:
            if sim:
                self.raiz.deiconify()
                self.raiz.attributes("-topmost", True)
            else:
                self.raiz.withdraw()
        except Exception:
            pass

    def bloquear(self, sim):
        """Bloqueado: os cliques passam para o jogo. Desbloqueado: arrasta o overlay com o rato."""
        self.bloqueado = sim
        r = self.raiz
        try:
            clique_atraves(r, sim)
            if sim:
                for ev in ("<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>"):
                    r.unbind(ev)
                if self.dica is not None:
                    self.dica.pack_forget()
            else:
                if self.dica is not None:
                    self.dica.pack(anchor="w", before=self.antes)
                r.bind("<ButtonPress-1>", self._carrega)
                r.bind("<B1-Motion>", self._arrasta)
                r.bind("<ButtonRelease-1>", self._larga)
        except Exception:
            pass

    def _carrega(self, e):
        self._p = (e.x_root - self.raiz.winfo_x(), e.y_root - self.raiz.winfo_y())

    def _arrasta(self, e):
        self.raiz.geometry("+%d+%d" % (e.x_root - self._p[0], e.y_root - self._p[1]))

    def _larga(self, e):
        if self.ao_mover:
            self.ao_mover(self.raiz.winfo_x(), self.raiz.winfo_y())

    def fechar(self):
        self.vivo = False
        try:
            self.raiz.destroy()
        except Exception:
            pass


def criar(pai=None, x=20, y=140, tamanho=1.0, opacidade=None, idioma="pt", sem_grelha=False,
          bloqueado=True, ao_mover=None):
    """Cria a janela por cima do jogo. Com `pai` (painel) é uma janela extra; sem ele é independente."""
    z = tamanho
    en = idioma == "en"
    vn = VN_EN if en else VN_PT

    def nome_l(n):
        return _nome_l(n, en)

    def f(n):
        return max(1, int(n * z))

    raiz = tk.Toplevel(pai) if pai is not None else tk.Tk()
    obj = Sobreposicao(raiz, ao_mover)
    raiz.title("Elementais")
    raiz.overrideredirect(True)
    raiz.attributes("-topmost", True)
    raiz.configure(bg=FUNDO)
    op = min(1.0, max(0.1, opacidade if opacidade is not None else ler_opacidade()))
    estado_op = {"v": op}
    try:
        raiz.attributes("-transparentcolor", FUNDO)
    except tk.TclError:
        pass
    try:
        raiz.attributes("-alpha", op)
    except tk.TclError:
        pass
    raiz.geometry("+%d+%d" % (x, y))

    # cartão do elemental novo (escondido até haver um)
    cartao = tk.Frame(raiz, bg=PAINEL, highlightthickness=2, highlightbackground="#4d9bff")
    foto = tk.Label(cartao, bg=PAINEL)
    foto.pack(side="left", padx=f(8), pady=f(8))
    caixa = tk.Frame(cartao, bg=PAINEL)
    caixa.pack(side="left", padx=(0, f(14)))
    tk.Label(caixa, text="NEW — ADDED TO COLLECTION" if en else "NOVO — FOI PARA A COLEÇÃO", bg=PAINEL, fg="#7fd0ff",
             font=("Segoe UI", f(9), "bold")).pack(anchor="w")
    nome = tk.Label(caixa, bg=PAINEL, fg=TXT, font=("Segoe UI", f(15), "bold italic"))
    nome.pack(anchor="w")
    raro = tk.Label(caixa, bg=PAINEL, fg=TXT, font=("Segoe UI", f(9), "bold"))
    raro.pack(anchor="w")

    # contador
    barra = tk.Frame(raiz, bg=PAINEL, padx=f(12), pady=f(8))
    barra.pack(anchor="w", pady=(f(8), 0))
    tk.Label(barra, text="SPRITES" if en else "ELEMENTAIS", bg=PAINEL, fg=TXT, font=("Segoe UI", f(11), "bold")).pack(side="left")
    cont = tk.Label(barra, text="0/%d" % TOTAL, bg=PAINEL, fg="#ffc83d", font=("Segoe UI", f(15), "bold"))
    cont.pack(side="left", padx=(f(14), 0))

    estado = {"n": None, "fim": 0.0, "img": None}
    obj.antes = barra
    obj.dica = tk.Label(raiz, text="MOVING: drag with the mouse  (Ctrl+Shift+L to lock)" if en
                        else "A MOVER: arrasta com o rato  (Ctrl+Shift+L para bloquear)",
                        bg="#ffc83d", fg="#000000", font=("Segoe UI", f(9), "bold"), padx=f(6), pady=f(2))

    # grelha com toda a coleção: silhueta preta = ainda não tens, imagem = já tens
    grelha = tk.Frame(raiz, bg=PAINEL, padx=f(6), pady=f(6))
    if not sem_grelha:
        grelha.pack(anchor="w", pady=(f(8), 0))
    passo = max(1, round(2 / z))                 # as miniaturas têm 96 px: 96/passo
    imgs, casas = {}, {}

    def mini(nome_f):
        try:
            im = tk.PhotoImage(master=raiz, file=os.path.join(REFS, "mini", nome_f))
            return im.subsample(passo, passo)
        except Exception:
            return None

    for n, i in enumerate(ORDEM):
        imgs[i] = (mini("sil_%02d.png" % (i + 1)), mini("%02d.png" % (i + 1)))
        casas[i] = tk.Label(grelha, bg=PAINEL, image=imgs[i][0], bd=0)
        casas[i].grid(row=n // 9, column=n % 9, padx=1, pady=1)
    pintado = set()

    def atualiza_grelha(achados):
        for i in ORDEM:
            tem = i in achados
            if tem != (i in pintado) and imgs[i][0] is not None:
                casas[i].configure(image=imgs[i][1 if tem else 0])
                (pintado.add if tem else pintado.discard)(i)

    def mostra(i):
        n, k, r = INFO[i]
        try:
            img = tk.PhotoImage(master=raiz, file=os.path.join(REFS, "%02d.png" % (i + 1)))
            fator = max(1, round(img.width() / f(76)))
            estado["img"] = img.subsample(fator, fator)
            foto.configure(image=estado["img"])
        except Exception:
            foto.configure(image="", text="")
        nome.configure(text="%s%s (%s)" % ("#%d " % NUM[i] if i in NUM else "", nome_l(n), vn[k]))
        raro.configure(text=(RN_EN[r] if en else r).upper(), fg=CORES[r])
        cartao.configure(highlightbackground=CORES[r])
        cartao.pack(anchor="w", before=barra)
        estado["fim"] = time.time() + 8

    def ciclo():
        if not obj.vivo:
            return
        ciclo_agora()
        if opacidade is None:
            novo = min(1.0, max(0.1, ler_opacidade()))
            if abs(novo - estado_op["v"]) > 0.005:
                estado_op["v"] = novo
                try:
                    raiz.attributes("-alpha", novo)
                except tk.TclError:
                    pass
        if estado["fim"] and time.time() > estado["fim"]:
            cartao.pack_forget()
            estado["fim"] = 0.0
        raiz.attributes("-topmost", True)
        raiz.after(1000, ciclo)

    def ciclo_agora():
        achados = ler()
        pid = perfis.indice()["ativo"]
        if estado.get("perfil") != pid:          # trocaste de conta: não é um elemental novo
            estado["perfil"] = pid
            estado["n"] = None
        cont.configure(text="%d/%d" % (len(achados), TOTAL))
        atualiza_grelha(set(achados))
        if estado["n"] is not None and len(achados) > estado["n"]:
            mostra(achados[-1])
        estado["n"] = len(achados)

    ciclo()
    obj.bloquear(bloqueado)
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--x", type=int, default=20)
    ap.add_argument("--y", type=int, default=140)
    ap.add_argument("--tamanho", type=float, default=1.0)
    ap.add_argument("--opacidade", type=float, default=None, help="0.1 (quase invisível) a 1 (opaco); sem isto usa o valor escolhido na página")
    ap.add_argument("--idioma", choices=["pt", "en"], default="pt", help="pt ou en")
    ap.add_argument("--sem-grelha", action="store_true", help="só contador e cartão, sem a grelha")
    a = ap.parse_args()
    o = criar(None, a.x, a.y, a.tamanho, a.opacidade, a.idioma, a.sem_grelha)
    print("Sobreposição ativa. Põe o Fortnite em 'Ecrã inteiro em janela'. (Ctrl+C para fechar)")
    try:
        o.raiz.mainloop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
