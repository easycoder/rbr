#!/bin/python3

from pathlib import Path
from easycoder import Program

Program(str(Path(__file__).resolve().with_name('rbrconf.ecs'))).start()
