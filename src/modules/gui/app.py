import sys
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication

from modules.backend import MockAgentsBackend, MockSessionStore
from modules.gui.controller import AppController
from modules.gui.loader import QmlReloader
from modules.gui.models import AgentListModel

COMPONENTS_DIR = Path(__file__).resolve().parent / "components"


def run() -> None:
    app = QApplication(sys.argv)

    engine = QQmlApplicationEngine()
    reloader = QmlReloader(engine, COMPONENTS_DIR)
    context = engine.rootContext()
    controller = AppController(MockAgentsBackend(), MockSessionStore())
    if context:
        context.setContextProperty("reloader", reloader)
        context.setContextProperty("controller", controller)
    engine.load(QUrl.fromLocalFile(str(COMPONENTS_DIR / "Main.qml")))
    if not engine.rootObjects():
        sys.exit(1)

    sys.exit(app.exec())
