import asyncio
import dataclasses
import enum
import os
import threading
import webbrowser
from pathlib import Path
from queue import Queue

import pystray
from PIL import Image
from PIL.Image import open as open_image

from main import Anime1WebApp

PRODUCT_NAME = "Anime1-LocalServer"

BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
LOG_DIR = BASE_DIR.joinpath("logs")
ICON_PATH = BASE_DIR.joinpath("assets", "icon.png")

HOST = "127.0.0.1"
PORT = 8520
DEBUG = False
USING_PROXY = False


class MsgType(enum.Enum):
    STOP_QUEUE = enum.auto()
    ERROR_EXIT = enum.auto()
    NOTIFY = enum.auto()


@dataclasses.dataclass
class Msg:
    type: MsgType
    content: str | None = None


def main() -> None:
    stray: pystray.Icon | None = None
    notify_queue: Queue = Queue()
    # noinspection HttpUrlsUsage
    server_url: str = f"http://{HOST}:{PORT}"
    icon: Image = open_image(ICON_PATH)
    app: Anime1WebApp = Anime1WebApp(LOG_DIR, DEBUG, USING_PROXY)

    def on_setup(i: pystray.Icon) -> None:
        i.visible = True
        while True:
            msg: Msg = notify_queue.get()
            match msg.type:
                case MsgType.NOTIFY:
                    if msg.content is not None:
                        i.notify(msg.content, PRODUCT_NAME)
                case MsgType.ERROR_EXIT:
                    i.remove_notification()
                    if msg.content is not None:
                        i.notify(msg.content, PRODUCT_NAME)
                    on_exit()
                case MsgType.STOP_QUEUE:
                    break

    def on_open() -> None:
        webbrowser.open(server_url)

    def on_logs() -> None:
        os.startfile(LOG_DIR)

    def on_system_proxy() -> None:
        app.update_using_proxy(not app.using_proxy)

    def on_reset_proxy_connection() -> None:
        app.reset_proxy_connection()
        notify_queue.put(Msg(MsgType.NOTIFY, "Proxy connection resettled"))

    def on_restart_server() -> None:
        threading.Thread(target=app.restart).start()
        notify_queue.put(Msg(MsgType.NOTIFY, "Server restarted"))

    def on_exit() -> None:
        notify_queue.put(Msg(MsgType.STOP_QUEUE))
        app.stop()
        if stray is not None:
            stray.stop()
        icon.close()

    menu = (
        pystray.MenuItem("Open browser", on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Show logs", on_logs),
        pystray.MenuItem("Using system proxy", on_system_proxy, lambda _: app.using_proxy),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Restart local server", on_restart_server),
        pystray.MenuItem("Reset all connection", on_reset_proxy_connection),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_exit)
    )
    stray = pystray.Icon(PRODUCT_NAME, icon, PRODUCT_NAME, menu)

    def launch_web_app() -> None:
        asyncio.set_event_loop(asyncio.new_event_loop())
        try:
            notify_queue.put(Msg(MsgType.NOTIFY, f"Start running: {server_url}"))
            app.run(HOST, PORT)
        except KeyboardInterrupt:
            on_exit()
        except Exception as e:
            notify_queue.put(Msg(MsgType.ERROR_EXIT, f"Error: {e}"))

    threading.Thread(target=launch_web_app).start()
    stray.run(on_setup)


if __name__ == "__main__":
    main()
