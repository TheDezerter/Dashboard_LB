# app/settings_window.py

from PyQt5 import QtWidgets, QtCore

from .settings import SETTINGS, DEFAULT_SETTINGS


class SettingsWindow(QtWidgets.QDialog):
    """
    Globalne ustawienia aplikacji.
    """

    def __init__(self, parent=None, current=None):
        super().__init__(parent)

        self._data = dict(current or SETTINGS)

        # usunięcie znaku zapytania
        flags = self.windowFlags()
        self.setWindowFlags(flags & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.setWindowTitle("Ustawienia globalne")
        self.setModal(True)
        self.setFixedSize(380, 300)

        form = QtWidgets.QFormLayout(self)

        # odświeżanie
        self.spin_refresh = QtWidgets.QSpinBox()
        self.spin_refresh.setRange(2, 3600)
        self.spin_refresh.setValue(int(self._data.get("refresh_interval", 10)))
        self.spin_refresh.setSuffix(" s")
        form.addRow("Interwał odświeżania:", self.spin_refresh)

        # dni historii
        self.spin_days = QtWidgets.QSpinBox()
        self.spin_days.setRange(1, 365)
        self.spin_days.setValue(int(self._data.get("history_days", 10)))
        self.spin_days.setSuffix(" dni")
        form.addRow("Dni przechowywania historii:", self.spin_days)

        # panele w rzędzie
        self.spin_panels = QtWidgets.QSpinBox()
        self.spin_panels.setRange(1, 12)
        self.spin_panels.setValue(int(self._data.get("panels_per_row", 5)))
        form.addRow("Panele w jednym rzędzie:", self.spin_panels)

        # temperatura min
        self.spin_tmin = QtWidgets.QDoubleSpinBox()
        self.spin_tmin.setRange(-40.0, 100.0)
        self.spin_tmin.setDecimals(1)
        self.spin_tmin.setSuffix(" °C")
        self.spin_tmin.setValue(
            float(self._data.get("temp_min", DEFAULT_SETTINGS["temp_min"]))
        )

        # temperatura max
        self.spin_tmax = QtWidgets.QDoubleSpinBox()
        self.spin_tmax.setRange(-40.0, 100.0)
        self.spin_tmax.setDecimals(1)
        self.spin_tmax.setSuffix(" °C")
        self.spin_tmax.setValue(
            float(self._data.get("temp_max", DEFAULT_SETTINGS["temp_max"]))
        )

        form.addRow("Temp. min:", self.spin_tmin)
        form.addRow("Temp. max:", self.spin_tmax)

        # wilgotność min
        self.spin_hmin = QtWidgets.QDoubleSpinBox()
        self.spin_hmin.setRange(0.0, 100.0)
        self.spin_hmin.setDecimals(1)
        self.spin_hmin.setSuffix(" %")
        self.spin_hmin.setValue(
            float(self._data.get("hum_min", DEFAULT_SETTINGS["hum_min"]))
        )

        # wilgotność max
        self.spin_hmax = QtWidgets.QDoubleSpinBox()
        self.spin_hmax.setRange(0.0, 100.0)
        self.spin_hmax.setDecimals(1)
        self.spin_hmax.setSuffix(" %")
        self.spin_hmax.setValue(
            float(self._data.get("hum_max", DEFAULT_SETTINGS["hum_max"]))
        )

        form.addRow("Hum. min:", self.spin_hmin)
        form.addRow("Hum. max:", self.spin_hmax)

        # przyciski
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

        # teksty przycisków
        btns.button(QtWidgets.QDialogButtonBox.Cancel).setText("Anuluj")
        btns.button(QtWidgets.QDialogButtonBox.Ok).setText("OK")

    # ------------------------------------------------------

    def get_settings(self) -> dict:
        return {
            "refresh_interval": int(self.spin_refresh.value()),
            "history_days": int(self.spin_days.value()),
            "panels_per_row": int(self.spin_panels.value()),
            "temp_min": float(self.spin_tmin.value()),
            "temp_max": float(self.spin_tmax.value()),
            "hum_min": float(self.spin_hmin.value()),
            "hum_max": float(self.spin_hmax.value()),
        }
