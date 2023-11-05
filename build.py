import os
import subprocess
import platform
import sys
from importlib.util import find_spec
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))

PRODUCT_NAME = "Anime1-LocalServer"
AUTHOR = "XFY9326"
VERSION = "0.0.0.3"
BUILD_DIR = "build"
MAIN_ENTRY = BASE_DIR.joinpath("tray.py")
ICON_PATH = BASE_DIR.joinpath("assets", "icon.png")
RESOURCES_MAP = {
    ICON_PATH: "assets/icon.png"
}

if __name__ == "__main__":
    if find_spec("nuitka") is None:
        assert os.system(f"{sys.executable} -m pip install nuitka") == 0, "Pip nuitka install failed!"

    # noinspection SpellCheckingInspection
    commands = [
        "nuitka",
        "--disable-console",
        "--onefile",
        "--follow-imports",
        "--assume-yes-for-downloads",
        f"--output-dir=\"{BUILD_DIR}\"",
        f"--output-filename=\"{PRODUCT_NAME}_{VERSION}\"",
        f"--product-name=\"{PRODUCT_NAME}\"",
        f"--file-description=\"{PRODUCT_NAME}\"",
        f"--file-version=\"{VERSION}\"",
        f"--product-version=\"{VERSION}\"",
        f"--company-name=\"{AUTHOR}\"",
        f"--copyright=\"© {AUTHOR}. All rights reserved.\"",
        "--onefile-tempdir-spec=\"%TEMP%/%PRODUCT%/%VERSION%\""
    ]
    if platform.system() == "Windows":
        commands.append(f"--windows-icon-from-ico=\"{ICON_PATH}\"")
    elif platform.system() == "Darwin":
        commands.append(f"--macos-app-icon=\"{ICON_PATH}\"")
    elif platform.system() == "Linux":
        commands.append(f"--linux-icon=\"{ICON_PATH}\"")
    for k, v in RESOURCES_MAP.items():
        commands.append(f"--include-data-files=\"{k}={v}\"")
    commands.append(str(MAIN_ENTRY))
    subprocess.call(f"{sys.executable} -m " + " ".join(commands))
