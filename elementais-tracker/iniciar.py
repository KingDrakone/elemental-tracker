#!/usr/bin/env python3
"""
Elementais do Fortnite — painel (abre tudo de uma vez).

  Início       estado, coleção, últimas atividades e ações
  Coleção      todos os elementais com raridades, variantes, busca e filtro
  Definições   liga/desliga cada parte e muda tamanho, opacidade, idioma...
  Ajuda

Teclas:  ↑ ↓ escolher   Enter confirmar   ← → separadores
No jogo: Ctrl+Shift+O mostra/esconde o overlay   Ctrl+Shift+L bloqueia/desbloqueia (para o mover)
"""
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque

import config
import dados
import perfis
import tracker

try:
    import tkinter as tk
    import sobreposicao
except Exception:            # sem tkinter: o painel e o rastreador funcionam, mas sem overlay no jogo
    tk = None
    sobreposicao = None

VERSAO = "1.0.0"
PAGINA = "https://claude.ai/artifact/MMcE3ryXf8oYKJc3kbwFgu"
ENDERECO = "http://localhost:%d/overlay" % tracker.PORTA

# ---------------------------------------------------------------- cores (ANSI)
def rgb(r, g, b, fundo=False):
    return "\x1b[%d;2;%d;%d;%dm" % (48 if fundo else 38, r, g, b)


# mesmas cores da página: fundo azul-petróleo, dourado, cartões cremes, cartão castanho
BG, INK = rgb(15, 27, 36, True), rgb(239, 226, 196)
R = "\x1b[0m" + BG + INK                                  # "repor" = fundo e texto da página
DIM, VERDE, AMAR, ROXO, VERM = rgb(184, 176, 160), rgb(86, 204, 128), rgb(255, 211, 106), rgb(181, 101, 255), rgb(255, 107, 90)
GOLD = rgb(201, 162, 79)
NEG = "\x1b[1m" + rgb(240, 192, 87)                        # títulos a dourado
SEL = rgb(201, 162, 79, True) + rgb(42, 28, 15)            # separador / opção ativa (dourado, texto escuro)
HERO = rgb(122, 74, 30, True) + rgb(251, 236, 196)         # cartão grande castanho
CARD = rgb(242, 230, 201, True) + rgb(42, 28, 15)          # cartão creme, texto escuro
CMUT = rgb(107, 90, 68)
CVERDE, CVERM = rgb(29, 122, 60), rgb(179, 38, 30)
LARGURA = 78
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def sem_cor(t):
    return ANSI.sub("", t)


def preenche(txt, fundo, w=LARGURA):
    """Linha com fundo a toda a largura (cartão)."""
    return fundo + txt + fundo + " " * max(0, w - len(sem_cor(txt))) + R


def navegador_app():
    """Caminho do Edge ou do Chrome (os dois sabem abrir uma página como janela com --app)."""
    cand = []
    if os.name == "nt":
        for var in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
            base = os.environ.get(var, "")
            if base:
                cand += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                         os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    for nome in ("msedge", "google-chrome", "chromium", "chromium-browser", "chrome"):
        cand.append(shutil.which(nome) or "")
    return next((c for c in cand if c and os.path.isfile(c)), None)


# ---------------------------------------------------------------- controlo (liga tudo)
class Controlo:
    def __init__(self):
        self.cfg = config.ler()
        self.registo = deque(maxlen=200)
        self.fila = queue.Queue()          # comandos para a thread do Tk
        self.sair = threading.Event()
        self.visivel = True
        self.ov = None
        self.raiz = None
        self.reset_armado = False
        self.ultima_conta = None
        self.rastreio = tracker.Rastreio(self.cfg["monitor"], 0.4, self.log)
        self.n_monitores = 1
        try:
            import mss
            with mss.mss() as s:
                self.n_monitores = max(1, len(s.monitors) - 1)
        except Exception:
            pass

    # -- registo de atividade
    def log(self, texto, tipo=""):
        if not tipo:
            tipo = "ok" if texto.startswith("Novo elemental") else ""
        self.registo.append((time.strftime("%H:%M:%S"), texto, tipo))

    # -- arranque
    def arrancar(self):
        tracker.ESTADO["obs"] = self.cfg["obs"]
        tracker.iniciar_servidor()
        self.log("Sincronização com a página disponível em %s" % ENDERECO.replace("/overlay", ""))
        if self.cfg["rastreio"]:
            self.rastreio.iniciar()
        n = perfis.limpar_automaticos()
        if n:
            self.log("Removidos %d perfis automáticos vazios (criados por engano)." % n)
        threading.Thread(target=self.vigia_conta, daemon=True).start()
        if self.cfg.get("abrir_pagina"):
            self.abrir_pagina()
        if tk is None and self.cfg["overlay_jogo"]:
            self.log("Sem tkinter: o overlay do jogo não está disponível neste PC.", "erro")
        else:
            self.fila.put(("recriar",))

    # -- ações vindas do painel / das teclas de atalho
    def alternar_visivel(self):
        self.visivel = not self.visivel
        self.fila.put(("visivel", self.visivel))
        self.log("Overlay %s." % ("visível" if self.visivel else "escondido"))

    def alternar_bloqueio(self):
        self.cfg = config.guardar(bloqueado=not self.cfg["bloqueado"])
        self.fila.put(("bloqueio", self.cfg["bloqueado"]))
        self.log("Overlay bloqueado (os cliques passam para o jogo)." if self.cfg["bloqueado"]
                 else "Overlay desbloqueado: arrasta-o com o rato.")

    def copiar_obs(self):
        self.fila.put(("copiar", ENDERECO))
        self.log("Endereço do OBS copiado: " + ENDERECO)

    def abrir_pagina(self):
        """Abre a página dos Elementais numa janela própria (sem separadores nem barra de endereço)."""
        url = "http://localhost:%d/pagina" % tracker.PORTA
        if not os.path.isfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pagina.html")):
            url = PAGINA
        exe = navegador_app()
        try:
            if exe:
                subprocess.Popen([exe, "--app=" + url, "--window-size=1100,820"])
                self.log("Página aberta numa janela.")
                return
        except Exception as e:
            self.log("Não consegui abrir a janela (%s); a abrir no navegador." % e, "erro")
        webbrowser.open(url)
        self.log("Página aberta no navegador.")

    def redefinir(self):
        tracker.guardar([])
        self.log("Todos os elementais foram redefinidos (0/%d)." % dados.TOTAL)

    # -- perfis (uma coleção por conta)
    def vigia_conta(self):
        """Deteta a mudança de conta no Fortnite e troca de perfil sozinho."""
        while not self.sair.is_set():
            if config.ler()["auto_perfil"]:
                try:
                    r = perfis.detetar()
                    if r and r[0] != self.ultima_conta:
                        primeira = self.ultima_conta is None
                        self.ultima_conta = r[0]
                        pf, mudou, nova = perfis.aplicar_conta(*r)
                        if nova:
                            self.log("Conta nova detetada (%s). Não crio perfis sozinho: usa 'Criar um perfil novo' em Definições." % (r[1] or r[0][:8]))
                        elif mudou:
                            self.log("Conta detetada: perfil '%s' (coleção trocada)." % pf["nome"])
                        elif primeira:
                            self.log("Conta detetada: perfil '%s'." % pf["nome"])
                except Exception as e:
                    self.log("Deteção da conta falhou: %s" % e, "erro")
            self.sair.wait(5)

    def mudar_perfil(self):
        pf = perfis.proximo()
        self.log("Perfil: '%s' (%d/%d elementais)." % (pf["nome"], len(tracker.ler_estado()), dados.TOTAL))

    def novo_perfil(self):
        pf = perfis.novo(conta=self.ultima_conta or "")
        perfis.trocar(pf["id"])
        self.log("Perfil novo '%s' criado e ativo (coleção vazia)." % pf["nome"])

    def diagnostico(self):
        pasta = perfis.pasta_logs()
        if not pasta or not os.path.isdir(pasta):
            self.log("Diagnóstico: não encontrei a pasta de logs do Fortnite (%s)." % (pasta or "sem LOCALAPPDATA"), "erro")
            return
        c = perfis.candidatos()
        self.log("Diagnóstico: %s" % ("; ".join("%s… x%d" % (i[:8], n) for i, n in c) if c else "nenhum id de conta no log."))
        self.log("A conta escolhida seria: %s" % (perfis.detetar() or ("nenhuma (sem certeza)",))[0][:8])

    def moveu(self, x, y):
        self.cfg = config.guardar(x=x, y=y)

    def alterar(self, chave):
        """Muda uma definição (Enter): liga/desliga ou passa ao valor seguinte."""
        c = config.ler()
        if chave in ("rastreio", "overlay_jogo", "obs"):
            novo = {chave: not c[chave]}
        elif chave == "estilo":
            novo = {chave: "simples" if c[chave] == "completo" else "completo"}
        elif chave == "idioma":
            novo = {chave: "en" if c[chave] == "pt" else "pt"}
        elif chave == "tamanho":
            t = c["tamanho"] + 10
            novo = {chave: 50 if t > 200 else t}
        elif chave == "opacidade":
            p = int(round(c["opacidade"] * 100)) + 10
            novo = {chave: 0.1 if p > 100 else p / 100}
        elif chave == "monitor":
            m = c["monitor"] + 1
            novo = {chave: 1 if m > self.n_monitores else m}
        elif chave == "pasta":
            self.abrir_pasta()
            return
        elif chave == "novo_perfil":
            self.novo_perfil()
            return
        elif chave == "diagnostico":
            self.diagnostico()
            return
        elif chave in ("auto_perfil", "abrir_pagina"):
            novo = {chave: not c[chave]}
        elif chave == "repor":
            padrao = dict(config.PADRAO)
            self.cfg = config.guardar(**padrao)
            self.aplicar_tudo()
            self.log("Definições repostas.")
            return
        else:
            return
        self.cfg = config.guardar(**novo)
        self.aplicar(chave)

    def aplicar(self, chave):
        c = self.cfg
        if chave == "rastreio":
            (self.rastreio.iniciar if c["rastreio"] else self.rastreio.parar)()
        elif chave == "monitor":
            self.rastreio.monitor = c["monitor"]
            if self.rastreio.ativo:
                self.rastreio.parar()
                self.rastreio.iniciar()
        elif chave == "obs":
            tracker.ESTADO["obs"] = c["obs"]
        elif chave in ("overlay_jogo", "estilo", "tamanho", "idioma"):
            self.fila.put(("recriar",))
        # opacidade: o overlay e o OBS leem config.json sozinhos

    def aplicar_tudo(self):
        for k in ("rastreio", "monitor", "obs", "overlay_jogo"):
            self.aplicar(k)

    def abrir_pasta(self):
        pasta = os.path.dirname(os.path.abspath(__file__))
        try:
            if os.name == "nt":
                os.startfile(pasta)
            else:
                webbrowser.open("file://" + pasta)
        except Exception:
            pass
        self.log("Pasta dos ficheiros: " + pasta)

    def fechar_tudo(self):
        self.rastreio.parar()
        self.sair.set()

    # -- corre na thread do Tk (a única que pode mexer nas janelas)
    def tratar_fila(self):
        while True:
            try:
                cmd = self.fila.get_nowait()
            except queue.Empty:
                break
            try:
                if cmd[0] == "recriar":
                    self._recriar()
                elif cmd[0] == "visivel" and self.ov:
                    self.ov.mostrar(cmd[1])
                elif cmd[0] == "bloqueio" and self.ov:
                    self.ov.bloquear(cmd[1])
                elif cmd[0] == "copiar" and self.raiz is not None:
                    self.raiz.clipboard_clear()
                    self.raiz.clipboard_append(cmd[1])
            except Exception as e:
                self.log("Erro: %s" % e, "erro")

    def _recriar(self):
        if self.ov is not None:
            self.ov.fechar()
            self.ov = None
        c = config.ler()
        self.cfg = c
        if not c["overlay_jogo"] or tk is None:
            return
        self.ov = sobreposicao.criar(self.raiz, c["x"], c["y"], c["tamanho"] / 100.0, None, c["idioma"],
                                     c["estilo"] == "simples", c["bloqueado"], self.moveu)
        self.ov.mostrar(self.visivel)


# ---------------------------------------------------------------- painel (texto)
TABS = ["Início", "Coleção", "Definições", "Ajuda"]
ACOES = [
    ("Abrir a página dos Elementais (janela)", "pagina"),
    ("Mostrar / esconder o overlay", "visivel"),
    ("Desbloquear / bloquear o overlay (para o mover)", "bloqueio"),
    ("Copiar o endereço do OBS", "obs"),
    ("Mudar de perfil (outra conta)", "perfil"),
    ("Redefinir elementais (apaga a coleção deste perfil)", "reset"),
    ("Sair", "sair"),
]


def ligado(b):
    return "ativado" if b else "desativado"


class Painel:
    def __init__(self, ctl):
        self.ctl = ctl
        self.tab = 0
        self.sel = [0, 0, 0, 0]
        self.rar = 0            # 0 = todas, 1..4 = Raro, Épico, Lendário, Mítico
        self.stat = 0           # 0 todos, 1 encontrados, 2 por encontrar
        self.busca = ""
        self.a_escrever = False

    # -- conteúdo das definições
    def definicoes(self):
        c = config.ler()
        return [
            ("Rastreador automático", "ligado" if c["rastreio"] else "desligado", "rastreio",
             "Lê o ecrã e guarda o elemental quando aparece 'NOVO - FOI PARA A COLEÇÃO'."),
            ("Overlay no jogo", ligado(c["overlay_jogo"]), "overlay_jogo",
             "Janela por cima do Fortnite (usa 'Ecrã inteiro em janela')."),
            ("Estilo do overlay", "grelha e cartão" if c["estilo"] == "completo" else "só contador e cartão",
             "estilo", "Completo mostra a coleção toda com silhuetas."),
            ("Tamanho do overlay", "%d%%" % c["tamanho"], "tamanho", "Enter aumenta de 10 em 10 e volta ao início."),
            ("Opacidade do overlay", "%d%%" % round(c["opacidade"] * 100), "opacidade",
             "Enter sobe de 10 em 10 e volta ao início (10% = quase invisível)."),
            ("Sobreposição OBS", ligado(c["obs"]), "obs", "Endereço: " + ENDERECO),
            ("Idioma dos overlays", "Português" if c["idioma"] == "pt" else "English", "idioma",
             "Nomes e textos do overlay do jogo e do OBS."),
            ("Detetar a conta automaticamente", ligado(c["auto_perfil"]), "auto_perfil",
             "Troca de coleção sozinho quando mudas de conta no Fortnite (melhor esforço)."),
            ("Abrir a página ao iniciar", ligado(c["abrir_pagina"]), "abrir_pagina",
             "Abre a página numa janela própria sempre que arrancas o painel."),
            ("Monitor a vigiar", "%d (de %d)" % (c["monitor"], self.ctl.n_monitores), "monitor",
             "O ecrã onde o Fortnite está."),
            ("Criar um perfil novo", "", "novo_perfil", "Uma coleção vazia para outra conta; fica ativa logo."),
            ("Diagnóstico da conta", "", "diagnostico", "Mostra na Atividade que contas o painel vê no log do Fortnite."),
            ("Abrir a pasta dos ficheiros", "", "pasta", "A pasta com o rastreador e o elementais.json."),
            ("Repor as definições", "", "repor", "Volta aos valores iniciais."),
        ]

    def n_itens(self):
        return len(ACOES) if self.tab == 0 else len(self.grupos()) if self.tab == 1 else len(self.definicoes()) if self.tab == 2 else 0

    # -- coleção (o mesmo que a página: raridades, variantes, busca, filtro)
    @staticmethod
    def norm(s):
        import unicodedata
        return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")

    def achados(self):
        return set(n - 1 for n in tracker.ler_estado() if (n - 1) in dados.INFO)

    def grupos(self):
        """[(raridade, nome_en, [índices])] depois da raridade, do filtro e da busca."""
        a = self.achados()
        termos = self.norm(self.busca.strip()).replace("tag:", " ").split()
        out = []
        for ri, (rar, gs) in enumerate(dados.RARS, 1):
            if self.rar and self.rar != ri:
                continue
            for nome, idx in gs:
                n = sum(1 for i in idx if i in a)
                if self.stat == 1 and n == 0:
                    continue
                if self.stat == 2 and n == len(idx):
                    continue
                if termos and not self.bate(termos, rar, nome, idx, n):
                    continue
                out.append((rar, nome, idx))
        return out

    def bate(self, termos, rar, nome, idx, n):
        """Busca por nome ou por tags: raridade, variante, número (#5), estado. Todos os termos têm de bater."""
        tags = [nome, dados.nome_l(nome, False), dados.nome_l(nome, True), rar, dados.RN_EN.get(rar, rar)]
        for k, i in enumerate(idx):
            tags += [dados.VN_PT[k], dados.VN_EN[k]]
            if i in dados.NUM:
                tags.append("#%d" % dados.NUM[i])
        if n > 0:
            tags += ["encontrado", "found"]
        if n < len(idx):
            tags += ["falta", "missing", "pendente"]
        if n == len(idx):
            tags += ["completo", "complete"]
        tags = [self.norm(x) for x in tags]
        return all((w in tags) if w.startswith("#") else any(not x.startswith("#") and w in x for x in tags) for w in termos)

    def marcar(self, idx_list):
        """Alterna os índices dados (se estão todos marcados, desmarca; senão marca os que faltam)."""
        a = self.achados()
        ordem = [n for n in tracker.ler_estado() if (n - 1) in dados.INFO]
        todos = all(i in a for i in idx_list)
        for i in idx_list:
            if todos and (i + 1) in ordem:
                ordem.remove(i + 1)
            elif not todos and (i + 1) not in ordem:
                ordem.append(i + 1)
        tracker.guardar(ordem)
        en = config.ler()["idioma"] == "en"
        if len(idx_list) == 1:
            self.ctl.log(("Marcado: " if not todos else "Desmarcado: ") + dados.descricao(idx_list[0], en))
        else:
            self.ctl.log(("Marcados todos: " if not todos else "Desmarcados todos: ") + dados.nome_l(dados.INFO[idx_list[0]][0], en))

    def tecla_colecao(self, t):
        gs = self.grupos()
        if self.a_escrever:
            if t == "sair":
                return False
            if t in ("enter", "esc"):
                self.a_escrever = False
            elif t in ("\x08", "\x7f"):
                self.busca = self.busca[:-1]
            elif isinstance(t, str) and len(t) == 1 and t.isprintable():
                self.busca += t
            self.sel[1] = 0
            return True
        if t == "/":
            self.a_escrever = True
            return True
        k = t.lower() if isinstance(t, str) and len(t) == 1 else t
        if k == "r":
            self.rar = (self.rar + 1) % (len(dados.RARS) + 1)
        elif k == "f":
            self.stat = (self.stat + 1) % 3
        elif k == "l":
            config.guardar(idioma="en" if config.ler()["idioma"] == "pt" else "pt")
        elif k == "c":
            self.busca = ""
            self.rar = self.stat = 0
        elif k in ("1", "2", "3") and gs:
            idx = gs[min(self.sel[1], len(gs) - 1)][2]
            v = int(k) - 1
            if v < len(idx):
                self.marcar([idx[v]])
            return True
        elif k == "enter" and gs:
            self.marcar(gs[min(self.sel[1], len(gs) - 1)][2])
            return True
        else:
            return False
        self.sel[1] = 0
        return True

    # -- teclas
    def tecla(self, t):
        ctl = self.ctl
        if self.tab == 1 and t and self.tecla_colecao(t):
            return
        if t == "esq":
            self.tab = (self.tab - 1) % len(TABS)
            ctl.reset_armado = False
        elif t == "dir":
            self.tab = (self.tab + 1) % len(TABS)
            ctl.reset_armado = False
        elif t in ("cima", "baixo") and self.n_itens():
            d = -1 if t == "cima" else 1
            self.sel[self.tab] = (self.sel[self.tab] + d) % self.n_itens()
            ctl.reset_armado = False
        elif t == "enter":
            if self.tab == 0:
                self.acao(ACOES[self.sel[0]][1])
            elif self.tab == 2:
                ctl.alterar(self.definicoes()[self.sel[2]][2])
        elif t == "sair":
            ctl.fechar_tudo()

    def acao(self, a):
        ctl = self.ctl
        if a != "reset":
            ctl.reset_armado = False
        if a == "pagina":
            ctl.abrir_pagina()
        elif a == "visivel":
            ctl.alternar_visivel()
        elif a == "bloqueio":
            ctl.alternar_bloqueio()
        elif a == "obs":
            ctl.copiar_obs()
        elif a == "perfil":
            ctl.mudar_perfil()
        elif a == "reset":
            if ctl.reset_armado:
                ctl.reset_armado = False
                ctl.redefinir()
            else:
                ctl.reset_armado = True
                ctl.log("Tens a certeza? Carrega Enter outra vez para apagar tudo.", "erro")
        elif a == "sair":
            ctl.fechar_tudo()

    # -- desenho
    def linhas(self):
        ctl = self.ctl
        L = [NEG + "Elementais do Fortnite" + R + DIM + "  v" + VERSAO + R,
             GOLD + "─" * LARGURA + R]
        L.append(" ".join((SEL + " %s " % n + R) if i == self.tab else (GOLD + "▏" + INK + "%s" % n + GOLD + "▕" + R) for i, n in enumerate(TABS)))
        L.append("")
        if self.tab == 0:
            L += self.inicio()
        elif self.tab == 1:
            L += self.colecao()
        elif self.tab == 2:
            L += self.def_linhas()
        else:
            L += self.ajuda()
        L.append("")
        L.append(GOLD + "╌" * LARGURA + R)
        if self.tab == 1:
            L.append(DIM + "↑ ↓ elemental   1 2 3 marca Normal/Valioso/Amaldiçoado   Enter marca todos   R raridade" + R)
            L.append(DIM + "F filtro   / buscar   L idioma   C limpar   ← → separadores" + R)
        else:
            L.append(DIM + "↑ ↓ escolher   Enter confirmar   ← → separadores" + R)
        L.append(DIM + "Overlay, mesmo no jogo: Ctrl+Shift+O mostrar / esconder   Ctrl+Shift+L bloquear" + R)
        return L

    def inicio(self):
        ctl = self.ctl
        c = config.ler()
        achados = [n - 1 for n in tracker.ler_estado() if (n - 1) in dados.INFO]
        tot = dados.TOTAL
        if ctl.rastreio.ativo:
            estado = VERDE + "À espera de um elemental novo" + R
        else:
            estado = AMAR + "Rastreador desligado" + R
        por_rar = []
        for rar, grupos in dados.RARS:
            n = sum(1 for _, idx in grupos for i in idx if i in achados)
            t = sum(len(idx) for _, idx in grupos)
            por_rar.append("%s %d/%d" % (rar, n, t))
        ultimo = DIM + "—" + R
        try:
            import json
            with open(tracker.SAIDA, encoding="utf-8") as f:
                d = json.load(f)
            if d.get("last") and (d["last"] - 1) in dados.INFO:
                ultimo = "%s  ·  %s" % (dados.descricao(d["last"] - 1, c["idioma"] == "en"), d.get("updated", "")[5:16])
        except Exception:
            pass
        vista = time.time() - tracker.ESTADO.get("pagina_visto", 0.0) < 6
        pagina = (VERDE + "página ligada" + R) if vista else (DIM + "à espera da página (abre-a ou recarrega com Ctrl+F5)" + R)
        if tk is None:
            ov = VERM + "indisponível (sem tkinter)" + R
        elif not c["overlay_jogo"]:
            ov = DIM + "desativado" + R
        else:
            ov = "%s · %s · %d%% tamanho · %d%% opacidade" % (
                "visível" if ctl.visivel else "escondido", "bloqueado" if c["bloqueado"] else AMAR + "desbloqueado (a mover)" + R,
                c["tamanho"], round(c["opacidade"] * 100))
        L = [
            "%-14s%s%s" % ("Perfil", NEG + perfis.ativo()["nome"] + R,
                           DIM + "  (%d %s neste PC)" % (len(perfis.lista()), "perfil" if len(perfis.lista()) == 1 else "perfis") + R),
            "%-14s%s" % ("Estado", estado),
            "%-14s%s%d/%d%s  ·  %d%%   %s%s%s" % ("Coleção", AMAR + "\x1b[1m", len(achados), tot, R, round(100 * len(achados) / tot),
                                                  DIM, "  ".join(por_rar), R),
            "%-14s%s" % ("Último", ultimo),
            "%-14s%s" % ("Sincronização", pagina),
            "%-14s%s" % ("Overlay jogo", ov),
            "%-14s%s%s" % ("Overlay OBS", ENDERECO + "  ", VERDE + "ativado" + R if c["obs"] else DIM + "desativado" + R),
            "",
        ]
        for i, (nome, a) in enumerate(ACOES):
            if a == "visivel":
                nome = "Esconder o overlay" if ctl.visivel else "Mostrar o overlay"
            elif a == "bloqueio":
                nome = "Desbloquear o overlay (para o mover)" if c["bloqueado"] else "Bloquear o overlay"
            elif a == "reset" and ctl.reset_armado:
                nome = "Redefinir elementais — Enter outra vez para confirmar"
            L.append((SEL + "› %s" % nome + R) if i == self.sel[0] else ("  " + nome))
        L += ["", NEG + "Atividade" + R]
        import textwrap
        reg = list(ctl.registo)[-8:]
        caixa = [preenche("", CARD)]
        for hora, texto, tipo in reg:
            if tipo == "ok":
                pre, cor = "✔ ", CVERDE
            elif tipo == "erro":
                pre, cor = "! ", CVERM
            else:
                pre, cor = "[%s] " % hora, CMUT
            for k, parte in enumerate(textwrap.wrap(texto, LARGURA - 4 - len(pre)) or [""]):
                caixa.append(preenche("  " + cor + (pre if k == 0 else " " * len(pre)) + parte, CARD))
        if not reg:
            caixa.append(preenche("  " + CMUT + "(ainda nada)", CARD))
        caixa.append(preenche("", CARD))
        return L + caixa

    def colecao(self):
        c = config.ler()
        en = c["idioma"] == "en"
        a = self.achados()
        tot = dados.TOTAL
        cheio = int(30 * len(a) / tot)
        COR = {"Raro": "\x1b[94m", "Épico": "\x1b[95m", "Lendário": "\x1b[93m", "Mítico": "\x1b[91m"}
        rn = lambda r: dados.RN_EN.get(r, r) if en else r
        vn = dados.VN_EN if en else dados.VN_PT
        L = [preenche(" ", HERO),
             preenche("  " + ("Unlocked sprites" if en else "Elementais desbloqueados"), HERO),
             preenche("  " + AMAR + "\x1b[1m%d/%d" % (len(a), tot) + HERO + "   " + AMAR + "█" * cheio + rgb(80, 50, 20) + "█" * (30 - cheio)
                      + HERO + "  %d%%" % round(100 * len(a) / tot), HERO),
             preenche(" ", HERO)]
        filtros = (["All", "Found", "Not found"] if en else ["Todos", "Encontrados", "Por encontrar"])[self.stat]
        rar = (("All" if en else "Todas") if not self.rar else rn(dados.RARS[self.rar - 1][0]))
        busca = self.busca + ("█" if self.a_escrever else "")
        L.append(DIM + ("Rarity: " if en else "Raridade: ") + R + NEG + rar + R + DIM + ("   Filter: " if en else "   Filtro: ") + R + NEG + filtros + R
                 + DIM + ("   Search: " if en else "   Busca: ") + R + (NEG + busca + R if (busca or self.a_escrever) else DIM + "—" + R)
                 + DIM + "   " + ("Language: " if en else "Idioma: ") + R + NEG + ("EN" if en else "PT") + R)
        L.append("")
        gs = self.grupos()
        if not gs:
            return L + [DIM + ("No sprites found" if en else "Nenhum elemental encontrado") + R]
        self.sel[1] = min(self.sel[1], len(gs) - 1)
        L.append(DIM + " " * 26 + "".join("%-13s" % v for v in vn) + R)
        atual = None
        for gi, (rar_, nome, idx) in enumerate(gs):
            if rar_ != atual:
                atual = rar_
                tg = [i for _, g in dados.RARS if _ == rar_ for _, ix in g for i in ix]
                L.append(COR[rar_] + NEG + rn(rar_) + R + DIM + " %d/%d" % (sum(1 for i in tg if i in a), len(tg)) + R)
            CORV = [rgb(180, 191, 224, True), rgb(243, 178, 97, True), rgb(143, 212, 154, True)]    # Normal, Valioso, Amaldiçoado
            cel = []
            for v in range(3):
                if v >= len(idx):
                    cel.append(CARD + " " * 12)
                    continue
                i = idx[v]
                num = "#%d" % dados.NUM[i] if i in dados.NUM else ""
                if i in a:
                    cel.append(CORV[v] + rgb(42, 28, 15) + "\x1b[1m ✔ %-6s " % num + CARD + "  ")
                else:
                    cel.append(rgb(228, 211, 173, True) + CMUT + " · %-6s " % num + CARD + "  ")
            n = sum(1 for i in idx if i in a)
            marca = (rgb(122, 74, 30) + "\x1b[1m› " if gi == self.sel[1] else "  ")
            nm = ("\x1b[1m" if gi == self.sel[1] else "") + "%-22s" % dados.nome_l(nome, en)[:21]
            L.append(preenche(CARD + marca + nm + "\x1b[22m " + "".join(cel) + CMUT + "%d/%d" % (n, len(idx)), CARD))
        return L

    def def_linhas(self):
        itens = self.definicoes()
        L = []
        for i, (nome, valor, _, _) in enumerate(itens):
            txt = "%s%s" % (nome, " : " + valor if valor else "")
            L.append((SEL + "› %s" % txt + R) if i == self.sel[2] else ("  " + txt))
        L += ["", DIM + itens[self.sel[2]][3] + R]
        return L

    def ajuda(self):
        return [
            NEG + "Como funciona" + R,
            "1. Deixa este painel aberto enquanto jogas (Fortnite em 'Ecrã inteiro em janela').",
            "2. Quando aparece 'NOVO - FOI PARA A COLEÇÃO', o rastreador reconhece o elemental,",
            "   guarda-o e mostra-o no overlay e na página (que sincroniza sozinha).",
            "3. Cada parte liga/desliga em Definições, sem fechar as outras.",
            "4. Em Coleção vês e marcas à mão os elementais (como na página): 1 2 3 variante,",
            "   Enter todos, R raridade, F filtro, / buscar, L idioma, C limpar.",
            "",
            NEG + "Contas" + R,
            "   Cada conta tem a sua coleção (perfil). Com a deteção automática ligada, o painel troca",
            "   de perfil quando mudas de conta no Fortnite. Se não detetar, usa 'Mudar de perfil'.",
            "",
            NEG + "Overlay no jogo" + R,
            "   Ctrl+Shift+O  mostra ou esconde      Ctrl+Shift+L  bloqueia ou desbloqueia",
            "   Desbloqueado, podes arrastá-lo com o rato; a posição fica guardada.",
            "   Bloqueado, os cliques passam para o jogo.",
            "",
            NEG + "OBS" + R,
            "   Fonte 'Navegador' com o endereço: " + ENDERECO,
            "   (opções: ?grelha=1  ?escala=1.5  ?fundo=0.2  ?lang=en)",
            "",
            NEG + "Ficheiros" + R,
            "   elementais.json (coleção)   config.json (definições)",
        ]


# ---------------------------------------------------------------- teclado e ecrã
def ler_tecla(espera=0.1):
    """Devolve 'cima','baixo','esq','dir','enter','esc','sair', um caracter, ou None."""
    if os.name == "nt":
        import msvcrt
        fim = time.time() + espera
        while time.time() < fim:
            if msvcrt.kbhit():
                c = msvcrt.getwch()
                if c in ("\x00", "\xe0"):
                    return {"H": "cima", "P": "baixo", "K": "esq", "M": "dir"}.get(msvcrt.getwch())
                return {"\r": "enter", "\x1b": "esc", "\x03": "sair"}.get(c, c)
            time.sleep(0.02)
        return None
    import select
    fd = sys.stdin.fileno()
    if not select.select([fd], [], [], espera)[0]:
        return None
    c = os.read(fd, 8).decode("utf-8", "ignore")      # lê direto do descritor (sem buffer do Python)
    if c.startswith("\x1b"):
        return {"\x1b[A": "cima", "\x1b[B": "baixo", "\x1b[D": "esq", "\x1b[C": "dir"}.get(c, "esc")
    return {"\n": "enter", "\r": "enter", "\x03": "sair"}.get(c[:1], c[:1] or None)


def atalhos_globais(ctl):
    """Windows: Ctrl+Shift+O e Ctrl+Shift+L funcionam mesmo com o jogo em primeiro plano."""
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        MOD = 0x0002 | 0x0004 | 0x4000      # CTRL | SHIFT | NOREPEAT
        u.RegisterHotKey(None, 1, MOD, 0x4F)    # O
        u.RegisterHotKey(None, 2, MOD, 0x4C)    # L
        msg = wintypes.MSG()
        while not ctl.sair.is_set():
            if u.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == 0x0312:
                    (ctl.alternar_visivel if msg.wParam == 1 else ctl.alternar_bloqueio)()
            else:
                time.sleep(0.05)
        u.UnregisterHotKey(None, 1)
        u.UnregisterHotKey(None, 2)
    except Exception as e:
        ctl.log("Atalhos globais indisponíveis: %s" % e, "erro")


def icone_da_janela():
    """Windows: troca o ícone da janela (barra de título e barra de tarefas) pelo do elemental."""
    try:
        import ctypes
        caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icone.ico")
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        u = ctypes.windll.user32
        if not hwnd or not os.path.isfile(caminho):
            return
        for tamanho, tipo in ((32, 1), (16, 0)):                  # 1 = ícone grande, 0 = pequeno
            h = u.LoadImageW(None, caminho, 1, tamanho, tamanho, 0x10)   # IMAGE_ICON, LR_LOADFROMFILE
            if h:
                u.SendMessageW(hwnd, 0x80, tipo, h)                       # WM_SETICON
    except Exception:
        pass


def preparar_terminal():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if os.name == "nt":
        os.system("")
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.GetStdHandle(-11)
            m = ctypes.c_ulong()
            k.GetConsoleMode(h, ctypes.byref(m))
            k.SetConsoleMode(h, m.value | 4)     # ANSI
        except Exception:
            pass
        os.system("mode con: cols=100 lines=42")
        icone_da_janela()
    sys.stdout.write("\x1b]0;Elementais do Fortnite %s\x07\x1b]11;#0f1b24\x07\x1b]10;#efe2c4\x07" % VERSAO + R + "\x1b[2J\x1b[?25l")
    sys.stdout.flush()


def desenhar(painel):
    linhas = painel.linhas()
    sys.stdout.write("\x1b[H" + R + "".join(l + R + "\x1b[K\n" for l in linhas) + R + "\x1b[J")
    sys.stdout.flush()


def ciclo_painel(painel, ctl):
    ult = None
    while not ctl.sair.is_set():
        t = ler_tecla(0.15)
        if t:
            painel.tecla(t)
        quadro = "\n".join(painel.linhas())
        if t or quadro != ult:
            ult = quadro
            desenhar(painel)


def main():
    ctl = Controlo()
    painel = Painel(ctl)
    ctl.arrancar()
    preparar_terminal()
    antigo = None
    if os.name != "nt" and sys.stdin.isatty():
        import termios
        import tty
        antigo = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    threading.Thread(target=ciclo_painel, args=(painel, ctl), daemon=True).start()
    threading.Thread(target=atalhos_globais, args=(ctl,), daemon=True).start()
    try:
        if tk is not None:
            ctl.raiz = tk.Tk()
            ctl.raiz.withdraw()

            def passo():
                ctl.tratar_fila()
                if ctl.sair.is_set():
                    ctl.raiz.quit()
                else:
                    ctl.raiz.after(100, passo)
            ctl.raiz.after(100, passo)
            ctl.raiz.mainloop()
        else:
            while not ctl.sair.is_set():
                time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        ctl.fechar_tudo()
        if antigo is not None:
            import termios
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, antigo)
        sys.stdout.write("\x1b]111\x07\x1b]110\x07\x1b[?25h\x1b[0m\x1b[2J\x1b[H")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
