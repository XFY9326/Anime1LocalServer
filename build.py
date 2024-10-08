import os
import platform
import subprocess
import sys
from pathlib import Path

import toml

BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
PROJECT_CONFIG = toml.load(BASE_DIR.joinpath("pyproject.toml"))

PRODUCT_NAME = PROJECT_CONFIG["tool"]["poetry"]["name"]
AUTHOR = ', '.join(PROJECT_CONFIG["tool"]["poetry"]["authors"])
VERSION = PROJECT_CONFIG["tool"]["poetry"]["version"]
BUILD_DIR = "build"
MAIN_ENTRY = BASE_DIR.joinpath("tray.py")
ICON_PATH = BASE_DIR.joinpath("assets", "icon.png")
RESOURCES_MAP = {
    ICON_PATH: "assets/icon.png"
}

# noinspection SpellCheckingInspection
EXCLUDE_MODULES = {
    "all": {"numpy"},
    "windows": {"pystray._darwin", "pystray._gtk", "pystray._xorg", "pystray._appindicator", "pystray._dummy"},
    "darwin": {"pystray._win32", "pystray._gtk", "pystray._xorg", "pystray._appindicator", "pystray._dummy"},
    "linux": {"pystray._darwin", "pystray._win32", "pystray._dummy"}
}

if __name__ == "__main__":
    NO_IMPORT_MODULES = list()
    NO_IMPORT_MODULES.extend(EXCLUDE_MODULES["all"])
    if platform.system() == "Windows":
        NO_IMPORT_MODULES.extend(EXCLUDE_MODULES["windows"])
    elif platform.system() == "Darwin":
        NO_IMPORT_MODULES.extend(EXCLUDE_MODULES["darwin"])
    elif platform.system() == "Linux":
        NO_IMPORT_MODULES.extend(EXCLUDE_MODULES["linux"])

    # noinspection SpellCheckingInspection
    args = [
        "--onefile",
        f"--nofollow-import-to={','.join(NO_IMPORT_MODULES)}",
        "--assume-yes-for-downloads",
        f"--output-dir={BUILD_DIR}",
        f"--output-filename={PRODUCT_NAME}_{VERSION}",
        f"--product-name={PRODUCT_NAME}",
        f"--file-description={PRODUCT_NAME}",
        f"--file-version={VERSION}",
        f"--product-version={VERSION}",
        f"--company-name={AUTHOR}",
        f"--copyright=© {AUTHOR}. All rights reserved.",
        "--onefile-tempdir-spec={TEMP}/{PRODUCT}/{VERSION}"
    ]
    if platform.system() == "Windows":
        args.append("--windows-console-mode=disable")
        args.append(f"--windows-icon-from-ico={ICON_PATH}")
    elif platform.system() == "Darwin":
        args.append("--macos-create-app-bundle")
        args.append(f"--macos-app-icon={ICON_PATH}")
    elif platform.system() == "Linux":
        args.append(f"--linux-icon={ICON_PATH}")
    for k, v in RESOURCES_MAP.items():
        args.append(f"--include-data-files={k}={v}")
    args.append(MAIN_ENTRY)
    subprocess.call([sys.executable, "-m", "nuitka"] + [str(i) for i in args])
