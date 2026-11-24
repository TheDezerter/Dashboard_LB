# app/device_panel.py

from datetime import datetime, timedelta
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore, QtGui

from .settings import SETTINGS
from .utils import save_device_history, trim_history_days, log_alert


class DevicePanel(QtWidgets.QFrame):

    dragStarted = QtCore.pyqtSignal(str)   # źródło – IP panelu
    dragDropped = QtCore.pyqtSignal(str)   # cel – IP panelu

    ALERT_BG = (
        "background-color: rgba(180,0,0,80); "
        "border: 2px solid red; border-radius: 10px;"
    )
    NORMAL_BG = (
        "background-color: #3a3a3a; "
        "border: 2px solid #666; border-radius: 10px;"
    )

    def __init__(
        self,
        ip: str,
        name: str,
        history: dict,
        device_settings: dict,
        parent,
        remove_callback,
        open_history_callback,
        open_settings_callback,
    ):
        super().__init__(parent)

        # wczesne inicjalizacje
        self.value_labels = {}
        self.info_labels = {}

        self.temp_curves = {}
        self.hum_curve = None

        self.drag_enabled = False
        self._drag_start_pos = None

        self.ip = ip
        self.name = name
        self.history = history or {"time": [], "t1": [], "t2": [], "t3": [], "hum": []}
        self.device_settings = device_settings or {}

        self.remove_callback = remove_callback
        self.open_history_callback = open_history_callback
        self.open_settings_callback = open_settings_callback

        self.online = False
        self._alert_active = False

        self.setAcceptDrops(True)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setStyleSheet(self.NORMAL_BG)

        self.tooltip_timer = QtCore.QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(QtWidgets.QToolTip.hideText)

        self.build_ui()

        QtCore.QTimer.singleShot(0, lambda: self.update_view(forced=True))

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    def build_ui(self):
        layout = self.layout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ------------------ TOP BAR ------------------
        top = QtWidgets.QHBoxLayout()

        self.status = QtWidgets.QLabel("●")
        self.status.setStyleSheet("color: red; font-size: 16px;")
        top.addWidget(self.status)

        self.title = QtWidgets.QLabel(self.name)
        self.title.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        top.addWidget(self.title)
        top.addStretch()

        # LOCK
        self.lock_btn = QtWidgets.QToolButton()
        self.lock_btn.setIcon(QtGui.QIcon("app/assets/lock_open.png"))
        self.lock_btn.setIconSize(QtCore.QSize(18, 18))
        self.lock_btn.setCheckable(True)
        self.lock_btn.setChecked(False)
        self.lock_btn.clicked.connect(self.toggle_lock)
        top.addWidget(self.lock_btn)

        # DRAG HANDLE
        self.drag_btn = QtWidgets.QToolButton()
        self.drag_btn.setIcon(QtGui.QIcon("app/assets/drag.png"))
        self.drag_btn.setIconSize(QtCore.QSize(18, 18))
        self.drag_btn.installEventFilter(self)
        top.addWidget(self.drag_btn)

        layout.addLayout(top)

        # ------------------ INFO GRID ------------------
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(3)
        layout.addLayout(grid)

        labels_left = [
            ("t1", "Temp1:", "#ffaa00"),
            ("t2", "Temp2:", "#44aaee"),
            ("t3", "Temp3:", "#dd55ff"),
            ("hum", "Hum:", "#22cc66"),
        ]

        labels_right = [
            ("ip", "IP:"),
            ("mac", "MAC:"),
            ("sn", "S/N:"),
            ("model", "Model:"),
        ]

        for row, (key, text, col) in enumerate(labels_left):
            grid.addWidget(self._lbl(text, col), row, 0)
            v = self._boxed_label("-")
            self.value_labels[key] = v
            grid.addWidget(v, row, 1)

        for row, (key, text) in enumerate(labels_right):
            grid.addWidget(self._lbl(text), row, 2)
            v = self._boxed_label("-", key)
            self.info_labels[key] = v
            grid.addWidget(v, row, 3)

        self.info_labels["mac"].installEventFilter(self)

        # ------------------ TEMP PLOT ------------------
        self.temp_plot = pg.PlotWidget()
        self.temp_plot.setBackground("#2a2a2a")
        self.temp_plot.setFixedHeight(120)
        self.temp_plot.setMouseEnabled(False, False)
        self.temp_plot.getAxis("bottom").setTicks([])
        self.temp_plot.wheelEvent = lambda ev: None

        self.temp_curves = {
            "t1": self.temp_plot.plot(pen=pg.mkPen(QtGui.QColor("#ffaa00"), width=2)),
            "t2": self.temp_plot.plot(pen=pg.mkPen(QtGui.QColor("#44aaee"), width=2)),
            "t3": self.temp_plot.plot(pen=pg.mkPen(QtGui.QColor("#dd55ff"), width=2)),
        }

        layout.addWidget(self.temp_plot)

        # ------------------ HUM PLOT ------------------
        self.hum_plot = pg.PlotWidget()
        self.hum_plot.setBackground("#2a2a2a")
        self.hum_plot.setFixedHeight(120)
        self.hum_plot.setMouseEnabled(False, False)
        self.hum_plot.getAxis("bottom").setTicks([])

        self.hum_curve = self.hum_plot.plot(pen=pg.mkPen(QtGui.QColor("#22cc66"), width=2))
        layout.addWidget(self.hum_plot)

        # ------------------ BUTTONS ------------------
        btns = QtWidgets.QHBoxLayout()

        b_hist = QtWidgets.QPushButton("Historia")
        b_set = QtWidgets.QPushButton("Ustawienia")
        b_del = QtWidgets.QPushButton("Usuń")

        b_hist.clicked.connect(lambda: self.open_history_callback(self))
        b_set.clicked.connect(lambda: self.open_settings_callback(self))
        b_del.clicked.connect(self.request_remove)

        for b in (b_hist, b_set, b_del):
            b.setStyleSheet(
                "QPushButton {background-color:#3a6ea5; color:white; "
                "border-radius:8px; padding:6px 14px; font-weight:bold;}"
            )

        btns.addWidget(b_hist)
        btns.addWidget(b_set)
        btns.addWidget(b_del)
        layout.addLayout(btns)

    # ---------------------------------------------------------
    # LABEL HELPERS
    # ---------------------------------------------------------

    def _lbl(self, text, color=None):
        l = QtWidgets.QLabel(text)
        if color:
            l.setStyleSheet(f"color:{color}; font-size:12px; font-weight:bold;")
        else:
            l.setStyleSheet("color:white; font-size:12px;")
        return l

    def _boxed_label(self, text, key=None):
        l = QtWidgets.QLabel(text)
        l.setAlignment(QtCore.Qt.AlignCenter)

        if key == "mac":
            l.setFont(QtGui.QFont("DejaVu Sans Mono"))
            l.setStyleSheet(
                "background:#1E1E1E; padding:2px; border:1px solid #555; border-radius:6px;"
            )
        else:
            l.setStyleSheet(
                "background:#1E1E1E; padding:3px; border:1px solid #555; border-radius:6px;"
            )

        return l

    # ---------------------------------------------------------
    # LOCK
    # ---------------------------------------------------------

    def toggle_lock(self):
        self.drag_enabled = not self.drag_enabled
        self.lock_btn.setIcon(
            QtGui.QIcon("app/assets/lock_closed.png" if self.drag_enabled else "app/assets/lock_open.png")
        )

    # ---------------------------------------------------------
    # EVENT FILTER
    # ---------------------------------------------------------

    def eventFilter(self, obj, event):
        # DRAG
        if obj == self.drag_btn and self.drag_enabled:
            if event.type() == QtCore.QEvent.MouseButtonPress:
                self._drag_start_pos = event.pos()
                return True

            if event.type() == QtCore.QEvent.MouseMove:
                if self._drag_start_pos and (event.pos() - self._drag_start_pos).manhattanLength() > 8:
                    self.start_drag()
                    self._drag_start_pos = None
                    return True

        # MAC autosize
        if obj == self.info_labels.get("mac"):
            if event.type() == QtCore.QEvent.Resize:
                QtCore.QTimer.singleShot(0, self.fit_mac_font)

        return super().eventFilter(obj, event)

    # ---------------------------------------------------------
    # START DRAG
    # ---------------------------------------------------------

    def start_drag(self):
        self.dragStarted.emit(self.ip)

        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        mime.setText(self.ip)
        drag.setMimeData(mime)

        pix = self.grab()
        drag.setPixmap(pix)
        drag.setHotSpot(QtCore.QPoint(pix.width() // 2, pix.height() // 2))

        self.setStyleSheet("background-color:#555; border:2px dashed #999; border-radius:10px;")
        drag.exec_(QtCore.Qt.MoveAction)
        self.setStyleSheet(self.NORMAL_BG)

    # ---------------------------------------------------------
    # DROP EVENTS
    # ---------------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and self.drag_enabled:
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() and self.drag_enabled:
            event.acceptProposedAction()

    def dropEvent(self, event):
        """
        Emitujemy **SWÓJ** IP jako target — to naprawia działanie drag&drop.
        """
        if self.drag_enabled:
            self.dragDropped.emit(self.ip)
            event.acceptProposedAction()

    # ---------------------------------------------------------
    # FIT MAC FONT
    # ---------------------------------------------------------

    def fit_mac_font(self):
        label = self.info_labels.get("mac")
        if not label:
            return

        text = label.text()
        if not text:
            return

        min_size = 6
        max_size = 14
        width = label.width() - 4

        font = label.font()
        best = min_size

        for size in range(min_size, max_size + 1):
            font.setPointSize(size)
            metrics = QtGui.QFontMetrics(font)
            if metrics.horizontalAdvance(text) <= width:
                best = size
            else:
                break

        font.setPointSize(best)
        label.setFont(font)

    # ---------------------------------------------------------
    # UPDATE INFO
    # ---------------------------------------------------------

    def update_info(self, info: dict | None):
        self.info_labels["ip"].setText(self.ip)

        if not info:
            return

        self.info_labels["mac"].setText(info.get("mac", "-") or "-")
        self.info_labels["sn"].setText(info.get("sn", "-") or "-")
        self.info_labels["model"].setText(info.get("model", "-") or "-")

        QtCore.QTimer.singleShot(0, self.fit_mac_font)

    # ---------------------------------------------------------
    # UPDATE SENSOR DATA
    # ---------------------------------------------------------

    def update_data(self, data, timestamp: datetime):
        if not data:
            if self.online:
                log_alert(self.ip, "Połączenie utracone")

            self.online = False
            self.status.setStyleSheet("color:red; font-size:16px;")
            return

        was_offline = not self.online
        self.online = True
        self.status.setStyleSheet("color:#00ff00; font-size:16px;")

        if was_offline:
            log_alert(self.ip, "Połączenie przywrócone")

        self.title.setText(data["name"] or self.ip)

        t1, t2, t3 = data["temps"]
        hum = data["humidity"]

        vals = {
            "t1": t1,
            "t2": t2,
            "t3": t3,
            "hum": hum,
        }

        for k, v in vals.items():
            text = "-" if v is None else (f"{v:.1f} %" if k == "hum" else f"{v:.1f} °C")
            color = self.get_value_color(k, v)

            self.value_labels[k].setText(text)
            self.value_labels[k].setStyleSheet(
                f"background:#1E1E1E; padding:3px; border:1px solid #555; "
                f"border-radius:6px; font-size:12px; color:{color}; font-weight:bold;"
            )

        # zapis historii
        self.history["time"].append(timestamp.isoformat())
        self.history["t1"].append(np.nan if t1 is None else float(t1))
        self.history["t2"].append(np.nan if t2 is None else float(t2))
        self.history["t3"].append(np.nan if t3 is None else float(t3))
        self.history["hum"].append(np.nan if hum is None else float(hum))

        trim_history_days(self.history)
        save_device_history(self.ip, self.history)

        self.update_view()

    # ---------------------------------------------------------
    # UPDATE VIEW / PLOTS
    # ---------------------------------------------------------

    def update_view(self, forced=False):
        if not self.history["time"]:
            return

        # convert history to numpy arrays replacing None → nan
        T1 = np.array([np.nan if v is None else float(v) for v in self.history["t1"]])
        T2 = np.array([np.nan if v is None else float(v) for v in self.history["t2"]])
        T3 = np.array([np.nan if v is None else float(v) for v in self.history["t3"]])
        HUM = np.array([np.nan if v is None else float(v) for v in self.history["hum"]])

        dt_list = [datetime.fromisoformat(t) for t in self.history["time"]]
        dt_last = dt_list[-1]
        dt_min = dt_last - timedelta(hours=1)

        idxs = [i for i, t in enumerate(dt_list) if t >= dt_min]
        if not idxs:
            return

        start = idxs[0]

        # regular 10-min grid
        grid_times = [dt_last - timedelta(minutes=m) for m in range(60, -1, -10)]
        xs = list(range(len(grid_times)))

        def nearest(target):
            return min(range(start, len(dt_list)), key=lambda i: abs(dt_list[i] - target))

        t1p = []
        t2p = []
        t3p = []
        hump = []

        for g in grid_times:
            idx = nearest(g)
            t1p.append(T1[idx])
            t2p.append(T2[idx])
            t3p.append(T3[idx])
            hump.append(HUM[idx])

        # Y ranges
        valid_t = [v for v in t1p if not np.isnan(v)]
        if valid_t:
            mn, mx = min(valid_t), max(valid_t)
            self.temp_plot.setYRange(mn - 5, mx + 5)

        valid_h = [v for v in hump if not np.isnan(v)]
        if valid_h:
            mn, mx = min(valid_h), max(valid_h)
            self.hum_plot.setYRange(max(0, mn - 5), min(100, mx + 5))

        # plot curves
        self.temp_curves["t1"].setData(xs, t1p)
        self.temp_curves["t2"].setData(xs, t2p)
        self.temp_curves["t3"].setData(xs, t3p)
        self.hum_curve.setData(xs, hump)

        self._apply_time_ticks(self.temp_plot, dt_last)
        self._apply_time_ticks(self.hum_plot, dt_last)

        self.update_alert_styling()

    # ---------------------------------------------------------
    # TIME TICKS
    # ---------------------------------------------------------

    def _apply_time_ticks(self, plot, dt_last):
        ticks = []
        for i, mins in enumerate(range(60, -1, -10)):
            label = (dt_last - timedelta(minutes=mins)).strftime("%H:%M")
            ticks.append((i, label))
        plot.getAxis("bottom").setTicks([ticks])

    # ---------------------------------------------------------
    # ALERT SYSTEM
    # ---------------------------------------------------------

    def _get_thresholds(self, key):
        cfg = self.device_settings or {}
        if key == "hum":
            return (
                cfg.get("hum_min", SETTINGS["hum_min"]),
                cfg.get("hum_max", SETTINGS["hum_max"]),
                cfg.get("alerts_enabled", True),
            )
        else:
            return (
                cfg.get("temp_min", SETTINGS["temp_min"]),
                cfg.get("temp_max", SETTINGS["temp_max"]),
                cfg.get("alerts_enabled", True),
            )

    def get_value_color(self, key, val):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "gray"

        minv, maxv, enabled = self._get_thresholds(key)
        if not enabled:
            return "lime"

        v = float(val)
        if v > maxv + 1 or v < minv - 1:
            return "red"
        return "lime"

    def update_alert_styling(self):
        cfg = self.device_settings or {}
        if not cfg.get("alerts_enabled", True):
            self.setStyleSheet(self.NORMAL_BG)
            self._alert_active = False
            return

        outliers = []
        for k in ("t1", "t2", "t3", "hum"):
            v = self.history[k][-1]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue

            minv, maxv, _ = self._get_thresholds(k)
            if v < minv - 1 or v > maxv + 1:
                outliers.append((k, v, minv, maxv))

        active = bool(outliers)
        self.setStyleSheet(self.ALERT_BG if active else self.NORMAL_BG)

        if active and not self._alert_active:
            msg = ", ".join(
                f"{k.upper()}={v:.1f} (min={mn}, max={mx})"
                for k, v, mn, mx in outliers
            )
            log_alert(self.ip, "Przekroczone progi: " + msg)

        elif not active and self._alert_active:
            log_alert(self.ip, "Parametry wróciły w normie")

        self._alert_active = active

    # ---------------------------------------------------------
    # REMOVE BUTTON
    # ---------------------------------------------------------

    def request_remove(self):
        msg = QtWidgets.QMessageBox(self.window())

        # USUNIĘCIE "?":
        flags = msg.windowFlags()
        msg.setWindowFlags(flags & ~QtCore.Qt.WindowContextHelpButtonHint)

        msg.setWindowModality(QtCore.Qt.ApplicationModal)
        msg.setWindowTitle("Potwierdzenie")
        msg.setText(f"Czy usunąć urządzenie {self.ip}?")

        btn_yes = msg.addButton("Tak", QtWidgets.QMessageBox.YesRole)
        msg.addButton("Anuluj", QtWidgets.QMessageBox.NoRole)

        msg.exec()

        if msg.clickedButton() == btn_yes:
            self.remove_callback(self)

    # ---------------------------------------------------------
    # APPLY DEVICE SETTINGS
    # ---------------------------------------------------------

    def apply_device_settings(self, cfg: dict):
        self.device_settings = cfg or {}
        self.update_alert_styling()
