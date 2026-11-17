# -*- coding: utf-8 -*-
"""Janela do programa (sem navegador): mostra o painel numa janela própria, com o ícone do elemental.
Usa o pywebview (Edge WebView2 no Windows). Uso: janela.py <endereço> [--fechar-tudo]"""
import os
import sys
import threading
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
TITULO = "Elementais do Fortnite"


def tracker_vivo(base):
    try:
        urllib.request.urlopen(base + "/painel/estado", timeout=2).close()
        return True
    except Exception:
        return False


def pedir_fecho(base):
    try:
        rq = urllib.request.Request(base + "/fechar", data=b"", method="POST", headers={"X-Vigia": "1"})
        urllib.request.urlopen(rq, timeout=3).close()
    except Exception:
        pass


def decorar_janela():
    """Windows: ícone do elemental na janela/barra de tarefas e barra de título da cor da página."""
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import byref, c_int, c_uint, c_void_p
        u = ctypes.windll.user32
        u.FindWindowW.restype = c_void_p
        u.LoadImageW.restype = c_void_p
        u.LoadImageW.argtypes = [c_void_p, ctypes.c_wchar_p, c_uint, c_int, c_int, c_uint]
        u.SendMessageW.argtypes = [c_void_p, c_uint, c_void_p, c_void_p]
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute.argtypes = [c_void_p, c_uint, c_void_p, c_uint]
        ico = os.path.join(AQUI, "icone.ico")
        grande, pequeno = None, None

        def atributo(hwnd, nr, valor):
            v = c_int(valor)
            dwm.DwmSetWindowAttribute(hwnd, nr, byref(v), 4)

        # várias tentativas: o Windows/pywebview podem repor o ícone e a cor depois de a janela abrir
        for i in range(40):
            hwnd = u.FindWindowW(None, TITULO)
            if hwnd:
                if grande is None:
                    grande = u.LoadImageW(None, ico, 1, 48, 48, 0x10)
                    pequeno = u.LoadImageW(None, ico, 1, 16, 16, 0x10)
                if grande:
                    u.SendMessageW(hwnd, 0x80, 1, grande)        # WM_SETICON, ICON_BIG
                if pequeno:
                    u.SendMessageW(hwnd, 0x80, 0, pequeno)       # ICON_SMALL
                for nr, val in ((20, 1), (19, 1),                # modo escuro da barra
                                (35, 0x241B0F),                  # cor da barra = fundo da página (#0f1b24)
                                (36, 0xC4E2EF),                  # cor do título (#efe2c4)
                                (34, 0x241B0F)):                 # cor da borda
                    atributo(hwnd, nr, val)
            time.sleep(0.5 if i < 20 else 2.0)
    except Exception:
        pass


def main():
    url = next((a for a in sys.argv[1:] if a.startswith("http")), "http://localhost:8765/painel")
    base = url.split("/painel")[0]
    fechar_tudo = "--fechar-tudo" in sys.argv
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KingDrakone.ElementaisDoFortnite")
        except Exception:
            pass
    import webview
    janela = webview.create_window(TITULO, url, width=1180, height=880, min_size=(900, 600),
                                   background_color="#0f1b24")

    def vigiar():                       # se o tracker fechar, esta janela fecha-se também
        falhas = 0
        while True:
            time.sleep(1.5)
            falhas = 0 if tracker_vivo(base) else falhas + 1
            if falhas >= 3:
                try:
                    janela.destroy()
                except Exception:
                    os._exit(0)
                return

    def arrancou():
        threading.Thread(target=decorar_janela, daemon=True).start()
        threading.Thread(target=vigiar, daemon=True).start()

    ico = os.path.join(AQUI, "icone.ico")
    try:
        webview.start(arrancou, gui="edgechromium" if os.name == "nt" else None, icon=ico)
    except TypeError:                   # versão do pywebview sem o parâmetro icon
        webview.start(arrancou, gui="edgechromium" if os.name == "nt" else None)
    if fechar_tudo:                     # modo programa: fechar a janela fecha o tracker
        pedir_fecho(base)


if __name__ == "__main__":
    main()
