# app/dashboard.py

import asyncio
import aiohttp
import json
from datetime import datetime

from PyQt5 import QtCore, QtWidgets
from qasync import asyncSlot

from .device_panel import DevicePanel
from .fetchers import fetch_device, fetch_device_info
from .utils import load_device_history, log_error
from .settings import SETTINGS, save_settings
from .settings_window import SettingsWindow
from .alerts_window import AlertsWindow
from .history_window import HistoryWindow
from .device_settings_dialog import DeviceSettingsDialog


INFO_REFRESH_INTERVAL_MS = 15 * 60 * 1000  # 15 min


class Dashboard(QtWidgets.QWidget):
    """
    Główne okno aplikacji z listą urządzeń + drag&drop paneli (bez rebuild).
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Dashboard urządzeń")
        self.resize(1400, 900)

        # Sesja aiohttp zostanie utworzona ASYNCHRONICZNIE po starcie event loop
        self.session = None
        QtCore.QTimer.singleShot(0, self._init_session_async)

        # urządzenia z pliku
        self.devices = self.load_devices()
        self.panels = []

        # pomocnicze dla drag&drop
        self._drag_source_ip = None

        main = QtWidgets.QVBoxLayout(self)

        # -----------------------------------------------------
        # TOP BAR
        # -----------------------------------------------------
        top = QtWidgets.QHBoxLayout()
        main.addLayout(top)

        btn_add = QtWidgets.QPushButton("Dodaj urządzenie")
        btn_add.clicked.connect(self.add_device_dialog)
        top.addWidget(btn_add)

        btn_alerts = QtWidgets.QPushButton("Alerty")
        btn_alerts.clicked.connect(self.open_alerts)
        top.addWidget(btn_alerts)

        btn_settings = QtWidgets.QPushButton("Ustawienia")
        btn_settings.clicked.connect(self.open_settings)
        top.addWidget(btn_settings)

        top.addStretch()

        # -----------------------------------------------------
        # SCROLL AREA
        # -----------------------------------------------------
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        main.addWidget(self.scroll)

        self.container = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(self.container)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setSpacing(8)
        self.scroll.setWidget(self.container)

        # create UI for panels
        self.build_panels()

        # -----------------------------------------------------
        # TIMERS
        # -----------------------------------------------------
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_all_async)
        self.apply_new_refresh_interval()
        self.timer.start()

        # /info every 15 minutes
        self.info_timer = QtCore.QTimer(self)
        self.info_timer.timeout.connect(self.update_info_async)
        self.info_timer.start(INFO_REFRESH_INTERVAL_MS)

        QtCore.QTimer.singleShot(200, self.update_info_async)



    # ---------------------------------------------------------
    # ASYNC — UTWORZENIE SESJI AIOHTTP
    # ---------------------------------------------------------

    @asyncSlot()
    async def _init_session_async(self):
        if self.session is None:
            try:
                self.session = aiohttp.ClientSession()
            except Exception as e:
                log_error("session", f"ClientSession init failed: {e}")


    # ---------------------------------------------------------
    # REFRESH INTERVAL
    # ---------------------------------------------------------

    def apply_new_refresh_interval(self):
        self.timer.setInterval(SETTINGS.get("refresh_interval", 10) * 1000)



    # ---------------------------------------------------------
    # CREATE PANELS (only on startup)
    # ---------------------------------------------------------

    def build_panels(self):
        """Tworzenie paneli TYLKO raz — nie będzie niszczone przy drag&drop."""
        self.panels.clear()

        columns = int(SETTINGS.get("panels_per_row", 5))
        if columns < 1:
            columns = 1

        for i, entry in enumerate(self.devices):
            ip = entry["ip"]
            name = entry.get("name", ip)
            dev_cfg = entry.get("settings", {})
            history = load_device_history(ip)
            info = entry.get("info")

            panel = DevicePanel(
                ip=ip,
                name=name,
                history=history,
                device_settings=dev_cfg,
                parent=self,
                remove_callback=self.remove_panel,
                open_history_callback=self.open_history,
                open_settings_callback=self.open_device_settings,
            )

            panel.dragStarted.connect(self.drag_started)
            panel.dragDropped.connect(self.drag_dropped)

            if info:
                panel.update_info(info)

            row = i // columns
            col = i % columns
            self.grid.addWidget(panel, row, col)

            self.panels.append(panel)


    # ---------------------------------------------------------
    # SWAP PANELI — NOWE! (bez przebudowy UI)
    # ---------------------------------------------------------

    def swap_panels(self, p1, p2):
        """Zamienia dwa widgety w grid layout — BEZ odświeżania!"""
        idx1 = self.grid.indexOf(p1)
        idx2 = self.grid.indexOf(p2)
        if idx1 == -1 or idx2 == -1:
            return

        r1, c1, _, _ = self.grid.getItemPosition(idx1)
        r2, c2, _, _ = self.grid.getItemPosition(idx2)

        self.grid.addWidget(p1, r2, c2)
        self.grid.addWidget(p2, r1, c1)



    # ---------------------------------------------------------
    # DRAG & DROP HANDLERS
    # ---------------------------------------------------------

    @QtCore.pyqtSlot(str)
    def drag_started(self, ip):
        self._drag_source_ip = ip

    @QtCore.pyqtSlot(str)
    def drag_dropped(self, target_ip):

        if not self._drag_source_ip:
            return

        if self._drag_source_ip == target_ip:
            self._drag_source_ip = None
            return

        src_panel = next((p for p in self.panels if p.ip == self._drag_source_ip), None)
        dst_panel = next((p for p in self.panels if p.ip == target_ip), None)

        if not src_panel or not dst_panel:
            self._drag_source_ip = None
            return

        if not (src_panel.drag_enabled and dst_panel.drag_enabled):
            self._drag_source_ip = None
            return

        # --- swap widgetów w gridzie ---
        self.swap_panels(src_panel, dst_panel)

        # --- swap w devices.json ---
        src_idx = next((i for i, d in enumerate(self.devices) if d["ip"] == src_panel.ip), None)
        dst_idx = next((i for i, d in enumerate(self.devices) if d["ip"] == dst_panel.ip), None)

        if src_idx is not None and dst_idx is not None:
            self.devices[src_idx], self.devices[dst_idx] = (
                self.devices[dst_idx],
                self.devices[src_idx],
            )
            self.save_devices()

        self._drag_source_ip = None



    # ---------------------------------------------------------
    # ASYNC – SENSOR DATA REFRESH
    # ---------------------------------------------------------

    @asyncSlot()
    async def update_all_async(self):
        if not self.panels or self.session is None:
            return

        timestamp = datetime.now()

        tasks = [fetch_device(self.session, p.ip) for p in self.panels]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            log_error("global", f"fetch error: {e}")
            return

        for panel, result in zip(self.panels, results):
            if isinstance(result, Exception):
                log_error(panel.ip, f"fetch_device error: {result}")
                panel.update_data(None, timestamp)
            else:
                panel.update_data(result, timestamp)



    # ---------------------------------------------------------
    # ASYNC – /info REFRESH
    # ---------------------------------------------------------

    @asyncSlot()
    async def update_info_async(self):
        if not self.panels or self.session is None:
            return

        tasks = [fetch_device_info(self.session, p.ip) for p in self.panels]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            log_error("global", f"fetch info error: {e}")
            return

        updated = False

        for panel, result in zip(self.panels, results):
            entry = next((d for d in self.devices if d["ip"] == panel.ip), None)
            if not entry:
                continue

            if isinstance(result, Exception) or result is None:
                panel.update_info(entry.get("info"))
                continue

            info = {
                "mac": result.get("mac"),
                "sn": result.get("sn"),
                "model": result.get("model"),
            }

            entry["info"] = info
            updated = True
            panel.update_info(info)

        if updated:
            self.save_devices()



    # ---------------------------------------------------------
    # ADD DEVICE
    # ---------------------------------------------------------

    def add_device_dialog(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Dodaj IP")
        dlg.setModal(True)
        dlg.setFixedSize(260, 120)

        flags = dlg.windowFlags()
        dlg.setWindowFlags(flags & ~QtCore.Qt.WindowContextHelpButtonHint)

        layout = QtWidgets.QVBoxLayout(dlg)
        layout.addWidget(QtWidgets.QLabel("Adres IP:"))

        ip_edit = QtWidgets.QLineEdit()
        layout.addWidget(ip_edit)

        btns = QtWidgets.QHBoxLayout()
        ok = QtWidgets.QPushButton("Dodaj")
        cancel = QtWidgets.QPushButton("Anuluj")
        ok.clicked.connect(dlg.accept)
        cancel.clicked.connect(dlg.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return

        ip = ip_edit.text().strip()
        if not ip:
            return

        if any(d["ip"] == ip for d in self.devices):
            QtWidgets.QMessageBox.warning(
                self, "Duplikat", f"Urządzenie {ip} już istnieje."
            )
            return

        self.devices.append({"ip": ip, "name": ip})
        self.save_devices()

        # nowy panel — budujemy tylko dla nowego elementu
        self._add_single_panel(ip)



    def _add_single_panel(self, ip):
        """Dodanie pojedynczego panelu bez przebudowy UI."""
        entry = next((d for d in self.devices if d["ip"] == ip), None)
        if not entry:
            return

        name = entry.get("name", ip)
        dev_cfg = entry.get("settings", {})
        history = load_device_history(ip)
        info = entry.get("info")

        panel = DevicePanel(
            ip=ip,
            name=name,
            history=history,
            device_settings=dev_cfg,
            parent=self,
            remove_callback=self.remove_panel,
            open_history_callback=self.open_history,
            open_settings_callback=self.open_device_settings,
        )

        panel.dragStarted.connect(self.drag_started)
        panel.dragDropped.connect(self.drag_dropped)

        if info:
            panel.update_info(info)

        columns = SETTINGS.get("panels_per_row", 5)
        total = len(self.panels)

        row = total // columns
        col = total % columns

        self.grid.addWidget(panel, row, col)
        self.panels.append(panel)



    # ---------------------------------------------------------
    # REMOVE PANEL
    # ---------------------------------------------------------

    def remove_panel(self, panel):
        """Usuń panel bez przebudowy UI."""
        idx = self.panels.index(panel)

        # usuń z layoutu
        self.grid.removeWidget(panel)
        panel.setParent(None)

        # usuń z listy
        self.panels.pop(idx)
        self.devices.pop(idx)
        self.save_devices()

        # popraw pozycje reszty paneli
        self._rebuild_grid_order_simple()



    def _rebuild_grid_order_simple(self):
        """Przeukłada istniejące panele według aktualnej kolejności bez niszczenia widgetów."""
        for i, panel in enumerate(self.panels):
            row = i // SETTINGS["panels_per_row"]
            col = i % SETTINGS["panels_per_row"]
            self.grid.addWidget(panel, row, col)

    # ---------------------------------------------------------
    # DEVICES.JSON
    # ---------------------------------------------------------

    def save_devices(self):
        try:
            with open("devices.json", "w", encoding="utf-8") as f:
                json.dump(self.devices, f, indent=4, ensure_ascii=False)
        except Exception as e:
            log_error("devices", f"save_devices error: {e}")

    def load_devices(self):
        try:
            with open("devices.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    # ---------------------------------------------------------
    # WINDOWS
    # ---------------------------------------------------------

    def open_settings(self):
        dlg = SettingsWindow(self, SETTINGS)

        if dlg.exec() == QtWidgets.QDialog.Accepted:
            new_settings = dlg.get_settings()

            SETTINGS.clear()
            SETTINGS.update(new_settings)
            save_settings(SETTINGS)

            self.apply_new_refresh_interval()

            self._rebuild_grid_order_simple()

            for p in self.panels:
                p.update_alert_styling()

    def open_alerts(self):
        AlertsWindow(self).exec()

    def open_history(self, panel: DevicePanel):
        HistoryWindow(self, panel).exec()

    def open_device_settings(self, panel: DevicePanel):
        entry = next((d for d in self.devices if d["ip"] == panel.ip), None)
        if not entry:
            return

        current = entry.get("settings", {})
        dlg = DeviceSettingsDialog(self, panel.name, current)

        if dlg.exec() == QtWidgets.QDialog.Accepted:
            new_cfg = dlg.get_settings()
            entry["settings"] = new_cfg
            self.save_devices()

            panel.apply_device_settings(new_cfg)
            panel.update_alert_styling()



    # ---------------------------------------------------------
    # CLOSE EVENT
    # ---------------------------------------------------------

    def closeEvent(self, event):
        if hasattr(self, "timer"):
            self.timer.stop()
        if hasattr(self, "info_timer"):
            self.info_timer.stop()

        # zamknij sesję aiohttp
        if self.session:
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.create_task(self.session.close())
            except RuntimeError:
                pass

        super().closeEvent(event)
