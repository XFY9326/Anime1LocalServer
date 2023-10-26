import os.path
import signal
import webbrowser
from pathlib import Path

import pystray
from PIL import Image

from main import build_server

PRODUCT_NAME = "Anime1-LocalServer"

BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
LOG_DIR = BASE_DIR.joinpath("logs")
ICON_PATH = BASE_DIR.joinpath("assets", "icon.png")

HOST = "127.0.0.1"
PORT = 8520


def main():
    stray: pystray.Icon | None = None
    server = build_server(HOST, PORT, LOG_DIR)
    server_url = f"http://{HOST}:{PORT}"

    def on_setup(i: pystray.Icon):
        i.visible = True
        i.notify(f"Start running at {server_url}", PRODUCT_NAME)

    def on_open():
        webbrowser.open(server_url)

    def on_logs():
        os.startfile(LOG_DIR)

    def on_exit():
        server.handle_exit(signal.SIGINT, None)
        if stray is not None:
            stray.stop()

    icon = Image.open(ICON_PATH)
    menu = (
        pystray.MenuItem("Open", on_open, default=True),
        pystray.MenuItem("Logs", on_logs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_exit)
    )
    stray = pystray.Icon(PRODUCT_NAME, icon, PRODUCT_NAME, menu)
    stray.run_detached(on_setup)

    server.run()


if __name__ == "__main__":
    main()
