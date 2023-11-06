import importlib
import os
import pkgutil
import platform
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))

PRODUCT_NAME = "Anime1-LocalServer"
AUTHOR = "XFY9326"
VERSION = "0.0.0.4"
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
EXCLUDE_WHITE_LIST_MODULES = {
    "PIL": {"_version", "_binary", "_util", "_imaging", "Image", "ExifTags", "ImageMode", "TiffTags",
            "ImageChops", "ImageFile", "ImagePalette", "ImageSequence", "GimpGradientFile", "GimpPaletteFile", "ImageColor", "PaletteFile",
            "PngImagePlugin", "IcoImagePlugin", "BmpImagePlugin"}
}

if __name__ == "__main__":
    if find_spec("nuitka") is None:
        assert os.system(f"{sys.executable} -m pip install nuitka") == 0, "Pip nuitka install failed!"

    NO_IMPORT_MODULES = list()
    NO_IMPORT_MODULES.extend(EXCLUDE_MODULES["all"])
    if platform.system() == "Windows":
        NO_IMPORT_MODULES.extend(EXCLUDE_MODULES["windows"])
    elif platform.system() == "Darwin":
        NO_IMPORT_MODULES.extend(EXCLUDE_MODULES["darwin"])
    elif platform.system() == "Linux":
        NO_IMPORT_MODULES.extend(EXCLUDE_MODULES["linux"])
    for module_name, keep_sub_module_names in EXCLUDE_WHITE_LIST_MODULES.items():
        module = importlib.import_module(module_name)
        sub_module_names = {name for _, name, _ in pkgutil.walk_packages(module.__path__, f"{module.__name__}.")}
        NO_IMPORT_MODULES.extend(sub_module_names - {f"{module_name}.{i}" for i in keep_sub_module_names})

    # noinspection SpellCheckingInspection
    commands = [
        "nuitka",
        "--disable-console",
        "--remove-output",
        "--onefile",
        "--follow-imports",
        f"--nofollow-import-to=\"{','.join(NO_IMPORT_MODULES)}\"",
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
