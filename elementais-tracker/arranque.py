# -*- coding: utf-8 -*-
"""Abrir e fechar o painel com o Fortnite: liga/desliga o vigia (vigiar.pyw) no arranque do Windows."""
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))


def _ficheiro():
    pasta = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    return os.path.join(pasta, "Elementais Vigia.vbs")


def disponivel():
    return os.name == "nt" and bool(os.environ.get("APPDATA"))


def ativo():
    return disponivel() and os.path.exists(_ficheiro())


def ativar():
    """Cria o arranque automático do vigia e põe-no a correr já. Devolve None ou uma mensagem de erro."""
    if not disponivel():
        return "só funciona no Windows"
    try:
        exe = sys.executable or "python"
        vigia = os.path.join(AQUI, "vigiar.pyw")
        linhas = ['Set s=CreateObject("WScript.Shell")',
                  's.CurrentDirectory="%s"' % AQUI,
                  's.Run """%s"" ""%s""", 0, False' % (exe, vigia)]
        os.makedirs(os.path.dirname(_ficheiro()), exist_ok=True)
        with open(_ficheiro(), "w", encoding="mbcs", errors="replace", newline="\r\n") as f:
            f.write("\n".join(linhas) + "\n")
        subprocess.Popen([exe, vigia], cwd=AQUI, creationflags=0x08000008,      # sem janela, independente do painel
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return None
    except Exception as e:
        return str(e)


def desativar():
    """Apaga o arranque automático (o vigia fecha-se sozinho em poucos segundos)."""
    try:
        for nome in ("Elementais Vigia.vbs", "Elementais Vigia.lnk"):
            p = os.path.join(os.path.dirname(_ficheiro()), nome)
            if os.path.exists(p):
                os.remove(p)
        return None
    except Exception as e:
        return str(e)
