import asyncio
import os
import sys
from pathlib import Path

import qasync
from dotenv import load_dotenv
from openai import AsyncOpenAI
from PyQt6.QtCore import QUrl
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication

from modules.backend import MockAgentsBackend, MockSessionBackend
from modules.gui.controller import AppController
from modules.gui.highlighter import CodeHighlighter
from modules.gui.loader import QmlReloader
from modules.server.server import Server
from modules.utils.logger import setup_logging

COMPONENTS_DIR = Path(__file__).resolve().parent / "components"

_ = load_dotenv()

setup_logging()


def main() -> None:
    _ = os.environ.setdefault("QT_QPA_PLATFORMTHEME", "xdgdesktopportal")
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    server = Server(
        AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1", api_key=os.getenv("API_KEY")
        )
    )

    engine = QQmlApplicationEngine()
    reloader = QmlReloader(engine, COMPONENTS_DIR)
    controller = AppController(MockAgentsBackend(server), MockSessionBackend())
    highlighter = CodeHighlighter()

    context = engine.rootContext()
    if context:
        context.setContextProperty("reloader", reloader)
        context.setContextProperty("controller", controller)
        context.setContextProperty("highlighter", highlighter)

    engine.load(QUrl.fromLocalFile(str(COMPONENTS_DIR / "Main.qml")))
    if not engine.rootObjects():
        sys.exit(1)

    with loop:
        loop.run_forever()

    del context
    del reloader
    del engine
    del controller
