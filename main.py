# main.py

import sys
import asyncio
from PyQt5 import QtWidgets, QtGui, QtCore
from qasync import QEventLoop

from app.dashboard import Dashboard
from app.styles import apply_dark_theme


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Ikona aplikacji (opcjonalnie)
    try:
        app.setWindowIcon(QtGui.QIcon("app/assets/icon.ico"))
    except Exception:
        pass

    apply_dark_theme()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # -------------------------------
    # Wyciszenie błędów asyncio (WinError 10054)
    # -------------------------------
    def silence_asyncio_exceptions(loop, context):
        err = context.get("exception")
        if isinstance(err, ConnectionResetError):
            return  # całkowite wyciszenie zrywanych połączeń

    loop.set_exception_handler(silence_asyncio_exceptions)

    # Tworzymy główne okno
    w = Dashboard()

    # Usunięcie "?" z tytułu okna
    flags = w.windowFlags()
    w.setWindowFlags(flags & ~QtCore.Qt.WindowContextHelpButtonHint)

    try:
        w.setWindowIcon(QtGui.QIcon("app/assets/icon.ico"))
    except Exception:
        pass

    w.show()

    # Uruchomienie pętli
    with loop:
        loop.run_forever()
