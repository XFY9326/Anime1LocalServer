import dataclasses
import enum
import os.path
import signal
import webbrowser
from pathlib import Path
from queue import Queue

import pystray
from PIL.Image import open as open_image

from main import launch_server

PRODUCT_NAME = "Anime1-LocalServer"

BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
LOG_DIR = BASE_DIR.joinpath("logs")
ICON_PATH = BASE_DIR.joinpath("assets", "icon.png")

HOST = "127.0.0.1"
PORT = 8520
DEBUG = False


class MsgType(enum.Enum):
    EXIT = enum.auto()
    ERROR_EXIT = enum.auto()
    NOTIFY = enum.auto()


@dataclasses.dataclass
class Msg:
    type: MsgType
    content: str | None = None


def main():
    stray: pystray.Icon | None = None
    notify_queue = Queue()
    server_url = f"http://{HOST}:{PORT}"
    icon = open_image(ICON_PATH)

    def on_setup(i: pystray.Icon):
        i.visible = True
        while True:
            msg: Msg = notify_queue.get()
            if msg.type == MsgType.EXIT:
                return
            elif msg.type == MsgType.ERROR_EXIT:
                i.remove_notification()
                i.notify(msg.content, PRODUCT_NAME)
                on_exit(True)
                return
            else:
                i.notify(msg.content, PRODUCT_NAME)

    def on_open():
        webbrowser.open(server_url)

    def on_logs():
        os.startfile(LOG_DIR)

    def on_exit(error_exit: bool):
        if not error_exit:
            notify_queue.put(Msg(MsgType.EXIT))
            signal.raise_signal(signal.SIGINT)
        if stray is not None:
            stray.stop()
        icon.close()

    menu = (
        pystray.MenuItem("Open", on_open, default=True),
        pystray.MenuItem("Logs", on_logs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", lambda: on_exit(False))
    )
    stray = pystray.Icon(PRODUCT_NAME, icon, PRODUCT_NAME, menu)
    stray.run_detached(on_setup)

    try:
        notify_queue.put(Msg(MsgType.NOTIFY, f"Start running: {server_url}"))
        launch_server(HOST, PORT, LOG_DIR, DEBUG)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        notify_queue.put(Msg(MsgType.ERROR_EXIT, f"Error: {e}"))


if __name__ == "__main__":
    main()
