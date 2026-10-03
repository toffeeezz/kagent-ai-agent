from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name
from pygments.style import Style
from pygments.styles import get_style_by_name
from pygments.token import _TokenType
from pygments.util import ClassNotFound
from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QTextDocument
from PyQt6.QtQuick import QQuickTextDocument


def _utf16_len(s: str) -> int:
    # Qt document offsets are UTF-16 code units; Python str indexes are code points
    return len(s.encode("utf-16-le")) // 2


class CodeHighlighter(QObject):
    def __init__(self, style: str = "monokai", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._style: type[Style] = get_style_by_name(style)
        self._formats: dict[_TokenType, QTextCharFormat | None] = {}

    def _format_for(self, ttype: _TokenType) -> QTextCharFormat | None:
        if ttype in self._formats:
            return self._formats[ttype]

        st = self._style.style_for_token(ttype)
        fmt: QTextCharFormat | None = None
        if st["color"] or st["bold"] or st["italic"] or st["underline"]:
            fmt = QTextCharFormat()
            if st["color"]:
                fmt.setForeground(QColor(f"#{st['color']}"))
            if st["bold"]:
                fmt.setFontWeight(QFont.Weight.Bold)
            if st["italic"]:
                fmt.setFontItalic(True)
            if st["underline"]:
                fmt.setFontUnderline(True)
        self._formats[ttype] = fmt
        return fmt

    @pyqtSlot(QQuickTextDocument, str)
    def attach(self, quick_doc: QQuickTextDocument, lang: str) -> None:
        doc: QTextDocument | None = quick_doc.textDocument()
        if doc is None or not lang.strip():
            return

        try:
            # No stripping/newline fixing, so token offsets match the document exactly
            lexer: Lexer = get_lexer_by_name(
                lang.strip().lower(), stripnl=False, ensurenl=False
            )
        except ClassNotFound:
            return  # unknown language: stays plain monospace

        text: str = doc.toPlainText()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        pos = 0
        for ttype, value in lexer.get_tokens(text):
            end = pos + _utf16_len(value)
            fmt = self._format_for(ttype)
            if fmt is not None and value.strip():
                cursor.setPosition(pos)
                cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
                cursor.mergeCharFormat(fmt)
            pos = end
        cursor.endEditBlock()
