#!/usr/bin/env python3
"""VS Code debug launcher for Controller/newController.ecs.

Run this file under the Python debugger to step through EasyCoder runtime code
and the launcher itself while executing newController.ecs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def add_easycoder_source_path() -> Path | None:
    """Add a local EasyCoder checkout to sys.path when available."""
    controller_dir = Path(__file__).resolve().parent

    candidates: list[Path] = []

    env_root = os.environ.get("EASYCODER_SRC")
    if env_root:
        candidates.append(Path(env_root).expanduser())

    # Local symlink created in this project: Controller/easycoder-src -> .../easycoder
    local_package_link = controller_dir / "easycoder-src"
    if local_package_link.exists():
        candidates.append(local_package_link.resolve().parent)

    candidates.append(Path("~/dev/easycoder/easycoder-py").expanduser())

    for root in candidates:
        if (root / "easycoder").is_dir():
            root_str = str(root)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)
            return root

    return None


def main() -> None:
    controller_dir = Path(__file__).resolve().parent

    script_name = sys.argv[1] if len(sys.argv) > 1 else "newController.ecs"
    script_path = (controller_dir / script_name).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"EasyCoder script not found: {script_path}")

    add_easycoder_source_path()

    from easycoder import Program

    os.chdir(controller_dir)
    Program(str(script_path)).start()


if __name__ == "__main__":
    main()
