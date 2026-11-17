# -*- coding: utf-8 -*-
"""Vigia o Fortnite: quando o jogo abre, abre também o painel dos Elementais (iniciar.bat).
Corre em segundo plano, sem janela. Instala-se com 'Abrir com o Fortnite.bat'."""
import os
import socket
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
PORTA_TRACKER = 8765          # o rastreador responde aqui quando já está aberto
PORTA_VIGIA = 8766            # impede dois vigias ao mesmo tempo
JOGO = "fortniteclient"       # FortniteClient-Win64-Shipping.exe (curto, porque o tasklist pode cortar o nome)
VER = "--ver" in sys.argv
LOG = os.path.join(AQUI, "vigia.log")
SEM_JANELA = 0x08000000
NOVA_CONSOLA = 0x00000010


def log(msg):
    linha = "%s  %s" % (time.strftime("%H:%M:%S"), msg)
    if VER:
        print(linha, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
        if os.path.getsize(LOG) > 100000:
            os.remove(LOG)
    except Exception:
        pass


def jogo_aberto():
    try:
        # stdin/stderr explícitos: sem eles o pythonw (sem janela) falha ao lançar processos
        r = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           creationflags=0 if VER else SEM_JANELA, timeout=20)
        return JOGO in r.stdout.decode("utf-8", "ignore").lower()
    except Exception as e:
        log("erro a ler a lista de processos: %r" % (e,))
        return False


def tracker_aberto():
    try:
        with socket.create_connection(("127.0.0.1", PORTA_TRACKER), timeout=0.5):
            return True
    except OSError:
        return False


def abrir_tracker():
    try:
        subprocess.Popen(["cmd", "/c", "iniciar.bat"], cwd=AQUI, creationflags=NOVA_CONSOLA,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("Fortnite aberto: a abrir o painel dos Elementais.")
    except Exception as e:
        log("erro a abrir o painel: %r" % (e,))


def fechar_tracker():
    try:
        import urllib.request
        rq = urllib.request.Request("http://127.0.0.1:%d/fechar" % PORTA_TRACKER, data=b"", method="POST",
                                    headers={"X-Vigia": "1"})
        urllib.request.urlopen(rq, timeout=3).close()
        log("Fortnite fechado: a fechar o painel dos Elementais.")
    except Exception as e:
        log("erro a fechar o painel: %r" % (e,))


def atalho_arranque():
    pasta = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    return os.path.join(pasta, "Elementais Vigia.vbs")


def main():
    trava = socket.socket()
    try:
        trava.bind(("127.0.0.1", PORTA_VIGIA))          # já há um vigia a correr
    except OSError:
        log("já há um vigia a correr; este fecha-se.")
        return
    log("vigia iniciado.")
    tinha_atalho = os.path.exists(atalho_arranque())
    estava_aberto = False
    fechados = 0
    while True:
        if tinha_atalho and not os.path.exists(atalho_arranque()):
            return                                       # desativaste o arranque automático: o vigia sai
        aberto = jogo_aberto()
        if aberto != estava_aberto:
            log("Fortnite %s." % ("aberto" if aberto else "fechado"))
        if aberto and not estava_aberto and not tracker_aberto():
            time.sleep(8)                                # deixa o jogo acabar de abrir
            abrir_tracker()
        if not aberto and estava_aberto:
            fechados = fechados + 1
            if fechados >= 2:                            # confirma duas vezes (evita falsos "fechado")
                if tracker_aberto():
                    fechar_tracker()
                estava_aberto = False
            time.sleep(5)
            continue
        fechados = 0
        estava_aberto = aberto
        time.sleep(5)


if __name__ == "__main__":
    main()
