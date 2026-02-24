import sys
import os
import io
import unittest
from contextlib import redirect_stdout

# Ensure the local easycoder package is used (workspace layout aware)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, '..'))
LOCAL_EASYCODER = os.path.abspath(os.path.join(REPO_ROOT, '..', '..', 'easycoder', 'easycoder-py'))
if os.path.isdir(LOCAL_EASYCODER) and LOCAL_EASYCODER not in sys.path:
    sys.path.insert(0, LOCAL_EASYCODER)

from easycoder import Program


class TestExampleECS(unittest.TestCase):
    def test_example_prints_value(self):
        """Run the tiny example ECS and assert it prints the expected value."""
        base = os.path.abspath(os.path.join(HERE, '..'))
        script = os.path.join(base, 'examples', 'example.ecs')
        self.assertTrue(os.path.isfile(script), f"Example script not found: {script}")

        buf = io.StringIO()
        with redirect_stdout(buf):
            # Running Program.start() prints to stdout via the core domain
            Program(script).start()

        out = buf.getvalue()
        # The example prints '123' — ensure that appears in the captured output
        self.assertIn('123', out)


if __name__ == '__main__':
    unittest.main()
