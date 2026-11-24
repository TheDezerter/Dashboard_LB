# app/alerts_window.py

from PyQt5 import QtWidgets, QtCore

from .utils import load_alerts, save_alerts


class AlertsWindow(QtWidgets.QDialog):
    """
    Okno wyświetlające listę alertów zapisanych w alerts.json.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # usunięcie "?" z tytułu okna
        flags = self.windowFlags()
        self.setWindowFlags(
            (flags & ~QtCore.Qt.WindowContextHelpButtonHint) |
            QtCore.Qt.Dialog |
            QtCore.Qt.WindowTitleHint |
            QtCore.Qt.WindowCloseButtonHint
        )

        self.setWindowTitle("Alerty")
        self.setModal(True)
        self.setFixedSize(700, 400)

        layout = QtWidgets.QVBoxLayout(self)

        # Tytuł
        title = QtWidgets.QLabel("Zarejestrowane alerty")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Tabela
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Czas", "Urządzenie", "Opis"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)

        # Przyciski na dole
        btns = QtWidgets.QHBoxLayout()
        self.btn_clear = QtWidgets.QPushButton("Wyczyść alerty")
        self.btn_close = QtWidgets.QPushButton("Zamknij")

        btns.addWidget(self.btn_clear)
        btns.addWidget(self.btn_close)
        layout.addLayout(btns)

        # logika
        self.btn_close.clicked.connect(self.close)
        self.btn_clear.clicked.connect(self.clear_alerts)

        # załaduj dane
        self.load_to_table()

    # ---------------------------------------------------------
    # ŁADOWANIE ALERTÓW
    # ---------------------------------------------------------

    def load_to_table(self):
        """Wstawia alerty do tabeli."""
        alerts = load_alerts()

        self.table.clearContents()
        self.table.setRowCount(0)

        if not alerts:
            self.table.setRowCount(1)
            item = QtWidgets.QTableWidgetItem("— brak zdarzeń —")
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.table.setItem(0, 0, item)
            self.table.setSpan(0, 0, 1, 3)
            return

        self.table.setRowCount(len(alerts))

        for row, a in enumerate(alerts):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(a.get("time", "")))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(a.get("ip", "")))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(a.get("msg", "")))

        self.table.resizeColumnsToContents()

    # ---------------------------------------------------------
    # CZYSZCZENIE ALERTÓW
    # ---------------------------------------------------------

    def clear_alerts(self):
        ask = QtWidgets.QMessageBox.question(
            self,
            "Potwierdzenie",
            "Usunąć wszystkie alerty?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if ask != QtWidgets.QMessageBox.Yes:
            return

        save_alerts([])     # wyczyszczenie pliku
        self.load_to_table()
