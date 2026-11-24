# app/history_window.py

from datetime import datetime, timedelta
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore, QtGui

from .utils import save_device_history


class HistoryWindow(QtWidgets.QDialog):
    """
    Okno wyświetlające pełną historię pomiarów urządzenia.
    Wykresy temperatur i wilgotności, eksport CSV, czyszczenie historii.
    """

    def __init__(self, parent, panel):
        super().__init__(parent)
        self.panel = panel

        # usunięcie znaku zapytania z okna
        flags = self.windowFlags()
        self.setWindowFlags(flags & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.setWindowTitle(f"Historia – {panel.name}")
        self.resize(1100, 600)

        layout = QtWidgets.QVBoxLayout(self)

        # ---------------------------------------------------------
        # WYKRES TEMPERATURY
        # ---------------------------------------------------------
        self.temp_plot = pg.PlotWidget()
        self.temp_plot.setBackground("#2a2a2a")
        self.temp_plot.showGrid(x=False, y=False)
        self.temp_plot.setLabel("left", "Temp (°C)")
        layout.addWidget(self.temp_plot)

        self.temp_curves = {
            "t1": self.temp_plot.plot(pen=pg.mkPen("#ffaa00", width=2)),
            "t2": self.temp_plot.plot(pen=pg.mkPen("#44aaee", width=2)),
            "t3": self.temp_plot.plot(pen=pg.mkPen("#dd55ff", width=2)),
        }

        self.temp_plot.scene().sigMouseMoved.connect(
            lambda pos: self._show_plot_tooltip(pos, self.temp_plot,
                                                ["t1", "t2", "t3"], "°C")
        )

        # ---------------------------------------------------------
        # WYKRES WILGOTNOŚCI
        # ---------------------------------------------------------
        self.hum_plot = pg.PlotWidget()
        self.hum_plot.setBackground("#2a2a2a")
        self.hum_plot.showGrid(x=False, y=False)
        self.hum_plot.setLabel("left", "Hum (%)")
        layout.addWidget(self.hum_plot)

        self.hum_curve = self.hum_plot.plot(pen=pg.mkPen("#22cc66", width=2))

        self.hum_plot.scene().sigMouseMoved.connect(
            lambda pos: self._show_plot_tooltip(pos, self.hum_plot,
                                                ["hum"], "%")
        )

        # ---------------------------------------------------------
        # PRZYCISKI
        # ---------------------------------------------------------
        btns = QtWidgets.QHBoxLayout()
        self.btn_export = QtWidgets.QPushButton("Eksport CSV")
        self.btn_clear = QtWidgets.QPushButton("Wyczyść historię")
        self.btn_close = QtWidgets.QPushButton("Zamknij")

        btns.addWidget(self.btn_export)
        btns.addWidget(self.btn_clear)
        btns.addStretch()
        btns.addWidget(self.btn_close)
        layout.addLayout(btns)

        self.btn_close.clicked.connect(self.close)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_clear.clicked.connect(self.clear_history)

        # załaduj dane na wykres
        self.refresh_plots()

    # ---------------------------------------------------------
    # TOOLTIPY WYKRESÓW
    # ---------------------------------------------------------

    def _show_plot_tooltip(self, pos, plot, keys, suffix):
        """
        Pokazuje tooltip dla punktów na wykresie historii.
        """
        h = self.panel.history
        if not h["time"]:
            QtWidgets.QToolTip.hideText()
            return

        vb = plot.getViewBox()
        mouse = vb.mapSceneToView(pos)
        x_val = mouse.x()

        dt_list = [datetime.fromisoformat(t) for t in h["time"]]
        total = len(dt_list)

        # poza zakresem
        if x_val < 0 or x_val >= total:
            QtWidgets.QToolTip.hideText()
            return

        idx = int(round(x_val))
        idx = max(0, min(idx, total - 1))

        dt = dt_list[idx]

        vals = []
        for key in keys:
            val = h[key][idx]
            if val is None:
                vals.append(f"{key.upper()}: -")
            else:
                vals.append(f"{key.upper()}: {val:.1f}{suffix}")

        text = f"{dt.strftime('%d.%m.%Y %H:%M:%S')}<br>" + "<br>".join(vals)

        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), text)

    # ---------------------------------------------------------
    # ODSWIEŻENIE WYKRESÓW
    # ---------------------------------------------------------

    def refresh_plots(self):
        h = self.panel.history
        if not h["time"]:
            return

        dt_list = [datetime.fromisoformat(t) for t in h["time"]]
        x = np.arange(len(dt_list))

        # -------------- TEMPERATURY --------------
        valid_t = [v for v in h["t1"] if v is not None]
        if valid_t:
            tmin = min(valid_t) - 5
            tmax = max(valid_t) + 5
        else:
            tmin, tmax = 0, 40

        self.temp_plot.setYRange(tmin, tmax)

        for key, curve in self.temp_curves.items():
            curve.setData(x, [v if v is not None else np.nan for v in h[key]])

        # -------------- WILGOTNOŚĆ --------------
        valid_h = [v for v in h["hum"] if v is not None]
        if valid_h:
            hmin = max(0, min(valid_h) - 5)
            hmax = min(100, max(valid_h) + 5)
        else:
            hmin, hmax = 0, 100

        self.hum_plot.setYRange(hmin, hmax)
        self.hum_curve.setData(x, [v if v is not None else np.nan for v in h["hum"]])

        self._apply_date_ticks(self.temp_plot, dt_list, x)
        self._apply_date_ticks(self.hum_plot, dt_list, x)

    # ---------------------------------------------------------
    # OŚ CZASU (DATY)
    # ---------------------------------------------------------

    def _apply_date_ticks(self, plot, dt_list, x_vals):
        if not dt_list:
            return

        ticks = []
        first = dt_list[0].replace(hour=12, minute=0, second=0, microsecond=0)
        if first < dt_list[0]:
            first += timedelta(days=1)

        curr = first
        last = dt_list[-1]

        while curr <= last:
            idx = min(range(len(dt_list)), key=lambda i: abs(dt_list[i] - curr))
            ticks.append((x_vals[idx], curr.strftime("%d.%m.%Y")))
            curr += timedelta(days=1)

        plot.getAxis("bottom").setTicks([ticks])

    # ---------------------------------------------------------
    # EKSPORT CSV
    # ---------------------------------------------------------

    def export_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Zapisz historię", "history.csv", "Pliki CSV (*.csv)"
        )

        if not path:
            return

        h = self.panel.history

        with open(path, "w", encoding="utf-8") as f:
            f.write("Timestamp,Temp1,Temp2,Temp3,Humidity\n")
            for t, t1, t2, t3, hum in zip(
                h["time"], h["t1"], h["t2"], h["t3"], h["hum"]
            ):
                f.write(f"{t},{t1 or ''},{t2 or ''},{t3 or ''},{hum or ''}\n")

    # ---------------------------------------------------------
    # CZYSZCZENIE HISTORII
    # ---------------------------------------------------------

    def clear_history(self):
        ask = QtWidgets.QMessageBox.question(
            self,
            "Potwierdzenie",
            "Wyczyścić historię?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if ask != QtWidgets.QMessageBox.Yes:
            return

        # reset historii
        self.panel.history = {"time": [], "t1": [], "t2": [], "t3": [], "hum": []}
        save_device_history(self.panel.ip, self.panel.history)

        self.temp_plot.clear()
        self.hum_plot.clear()
