"""
Minimal harness to run the example ECS script with the local easycoder package.

Usage:
  python3 examples/run_example.py

This script ensures the local `easycoder` package directory is on sys.path
so the repository copy is used instead of any installed package.
"""
import sys, os

# Add the local easycoder package to sys.path (adjust if your workspace layout differs)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, '..'))
LOCAL_EASYCODER = os.path.abspath(os.path.join(REPO_ROOT, '..', '..', 'easycoder', 'easycoder-py'))
if os.path.isdir(LOCAL_EASYCODER) and LOCAL_EASYCODER not in sys.path:
    sys.path.insert(0, LOCAL_EASYCODER)

from easycoder import Program

if __name__ == '__main__':
    script = os.path.join(HERE, 'example.ecs')
    print(f"Running example ECS: {script}")
    Program(script).start()
