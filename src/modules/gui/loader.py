from pathlib import Path
from typing import final

from PyQt6.QtCore import QFileSystemWatcher, QObject, QTimer, pyqtSignal
from PyQt6.QtQml import QQmlApplicationEngine


@final
class QmlReloader(QObject):
    reload = pyqtSignal()

    def __init__(self, engine: QQmlApplicationEngine, qml_dir: Path) -> None:
        super().__init__()
        self._engine = engine
        self._dir = qml_dir
        self._watcher = QFileSystemWatcher(self)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(150)

        self._timer.timeout.connect(self._fire)
        self._watcher.fileChanged.connect(self._schedule)
        self._watcher.directoryChanged.connect(self._schedule)
        self._rewatch()

    def _schedule(self, _path: str) -> None:
        self._timer.start()

    def _rewatch(self) -> None:
        paths = [str(self._dir)]
        paths += [str(p) for p in self._dir.rglob("*") if p.is_dir()]
        paths += [str(p) for p in self._dir.rglob("*.qml")]
        paths += [str(p) for p in self._dir.rglob("qmldir")]
        known = set(self._watcher.files()) | set(self._watcher.directories())
        missing = [p for p in paths if p not in known]
        if missing:
            self._watcher.addPaths(missing)

    def _fire(self) -> None:
        self._engine.clearComponentCache()  # otherwise Qt serves the old compiled files
        self.reload.emit()
        self._rewatch()  # re-add paths the editor replaced
