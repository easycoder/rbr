#!/usr/bin/env python3

import os
import sys
from pathlib import Path


def add_easycoder_source_path() -> None:
    source_root = Path(
        os.environ.get("EASYCODER_SRC", "~/dev/easycoder/easycoder-py")
    ).expanduser()
    if source_root.is_dir():
        sys.path.insert(0, str(source_root))


add_easycoder_source_path()

from easycoder import Program

script_dir = Path(__file__).resolve().parent
os.chdir(script_dir)

Program(str(script_dir / "newController.ecs")).start()
