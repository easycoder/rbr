"""Headless check for the Studio's view-pane plugin.

Loads studio_ui.py through AllSpeak's own plugin mechanism, places the pane in
a panes splitter, points it at a local JPEG endpoint and waits for the frame.
No browser is needed; this is about the widget and the plumbing around it.

    cd tools/rbr-studio
    QT_QPA_PLATFORM=offscreen python3 tests/view_pane_check.py
"""

import os
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[1]
os.chdir(STUDIO)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from allspeak.as_program import Program  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"ok  {message}")


def make_jpeg(path):
    image = QImage(16, 24, QImage.Format.Format_RGB32)
    image.fill(QColor("#336699"))
    if not image.save(str(path), "JPEG"):
        raise AssertionError("could not write the test JPEG")
    return path.read_bytes()


class Handler(BaseHTTPRequestHandler):
    payload = b""

    def log_message(self, *args):
        pass

    def do_GET(self):
        body = self.payload
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    app = QApplication([])
    jpeg = make_jpeg(Path(tempfile.gettempdir()) / "studio-view-check.jpg")
    Handler.payload = jpeg
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/frame.jpg"

    script = Path(tempfile.mkdtemp(prefix="rbr-view-pane-")) / "pane.allspeak"
    script.write_text(
        "use graphics\n"
        "load plugin Studio_UI from studio_ui.py\n"
        "init graphics\n"
        "\n"
        "window Win\n"
        "layout Root\n"
        "panes Work\n"
        "create Win title `View pane check` at 0 0 size 640 480\n"
        "create Root type QVBoxLayout\n"
        "create Work orientation horizontal\n"
        "viewpane ViewPane\n"
        "create ViewPane\n"
        "place ViewPane in Work\n"
        f"set the source of ViewPane to `{url}`\n"
        "add Work to Root\n"
        "set the layout of Win to Root\n"
        "show Win\n",
        encoding="utf-8")

    program = Program(str(script), testMode=False)
    outcome = {"ok": False, "message": "the check did not run"}

    def inspect():
        try:
            holder = program.code[program.symbols["ViewPane"]]["object"]
            pane = holder.getValue()
            check(pane is not None, "create makes the view pane widget")
            work = program.code[program.symbols["Work"]]["object"].getValue()
            check(work.count() == 1, "place puts the pane in the panes splitter")

            deadline = time.time() + 10
            while time.time() < deadline and pane._frame is None:
                app.processEvents()
                time.sleep(0.05)
            check(pane._frame is not None, "the pane fetches the frame")
            check(pane._frame.width() == 16 and pane._frame.height() == 24,
                  "the fetched frame keeps its size")
            pane.clear()
            check(pane._frame is None, "clear drops the frame")
            outcome.update(ok=True, message="view pane check passed")
        except Exception as exc:  # noqa: BLE001 - the check reports the reason
            outcome.update(ok=False, message=str(exc))
        finally:
            QApplication.quit()

    QTimer.singleShot(2000, inspect)
    try:
        program.start()
    finally:
        server.shutdown()
        server.server_close()
    if not outcome["ok"]:
        raise SystemExit(outcome["message"])
    print(f"ok  {outcome['message']}")


if __name__ == "__main__":
    main()
