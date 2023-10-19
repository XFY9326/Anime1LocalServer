import os
import sys
from importlib.util import find_spec

PRODUCT_NAME = "Anime1-LocalServer"
AUTHOR = "XFY9326"
VERSION = "0.0.0.1"
BUILD_DIR = "build"
MAIN_ENTRY = ".\\main.py"

INCLUDE_PACKAGE_DATA = [
    "fake_useragent"
]

if __name__ == "__main__":
    if find_spec("nuitka") is None:
        assert os.system(f"{sys.executable} -m pip install nuitka") == 0, "Pip nuitka install failed!"

    # noinspection SpellCheckingInspection
    commands = [
        "nuitka",
        "--enable-console",
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
        f"--copyright=\"© {AUTHOR}. All rights reserved.\""
    ]
    for pkg in INCLUDE_PACKAGE_DATA:
        commands.append(f"--include-package-data=\"{pkg}\"")
    commands.append(MAIN_ENTRY)
    os.system(f"{sys.executable} -m " + " ".join(commands))
