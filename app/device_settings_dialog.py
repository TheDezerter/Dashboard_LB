# app/device_settings_dialog.py

from PyQt5 import QtWidgets, QtCore
from .settings import SETTINGS


class DeviceSettingsDialog(QtWidgets.QDialog):
    """
    Ustawienia indywidualne dla pojedynczego urządzenia.
    """

    def __init__(self, parent, dev_name: str, current: dict | None):
        super().__init__(parent)

        # usunięcie znaku zapytania z okna
        flags = self.windowFlags()
        self.setWindowFlags(flags & ~QtCore.Qt.WindowContextHelpButtonHint)

        self._current = current or {}

        self.setWindowTitle(f"Ustawienia – {dev_name}")
        self.setModal(True)
        self.setFixedSize(360, 230)

        form = QtWidgets.QFormLayout(self)

        # ALERTY
        self.chk_alerts = QtWidgets.QCheckBox("Włącz alerty dla tego urządzenia")
        self.chk_alerts.setChecked(self._current.get("alerts_enabled", True))
        form.addRow(self.chk_alerts)

        # TEMPERATURA MIN
        self.spin_tmin = QtWidgets.QDoubleSpinBox()
        self.spin_tmin.setRange(-40.0, 100.0)
        self.spin_tmin.setDecimals(1)
        self.spin_tmin.setSuffix(" °C")
        self.spin_tmin.setValue(float(self._current.get("temp_min", SETTINGS["temp_min"])))

        # TEMPERATURA MAX
        self.spin_tmax = QtWidgets.QDoubleSpinBox()
        self.spin_tmax.setRange(-40.0, 100.0)
        self.spin_tmax.setDecimals(1)
        self.spin_tmax.setSuffix(" °C")
        self.spin_tmax.setValue(float(self._current.get("temp_max", SETTINGS["temp_max"])))

        form.addRow("Temp. min:", self.spin_tmin)
        form.addRow("Temp. max:", self.spin_tmax)

        # WILGOTNOŚĆ MIN
        self.spin_hmin = QtWidgets.QDoubleSpinBox()
        self.spin_hmin.setRange(0.0, 100.0)
        self.spin_hmin.setDecimals(1)
        self.spin_hmin.setSuffix(" %")
        self.spin_hmin.setValue(float(self._current.get("hum_min", SETTINGS["hum_min"])))

        # WILGOTNOŚĆ MAX
        self.spin_hmax = QtWidgets.QDoubleSpinBox()
        self.spin_hmax.setRange(0.0, 100.0)
        self.spin_hmax.setDecimals(1)
        self.spin_hmax.setSuffix(" %")
        self.spin_hmax.setValue(float(self._current.get("hum_max", SETTINGS["hum_max"])))

        form.addRow("Hum. min:", self.spin_hmin)
        form.addRow("Hum. max:", self.spin_hmax)

        # PRZYCISKI OK / ANULUJ
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        form.addRow(btns)

        btns.button(QtWidgets.QDialogButtonBox.Cancel).setText("Anuluj")
        btns.button(QtWidgets.QDialogButtonBox.Ok).setText("OK")

        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

    # ------------------------------------------------------
    # ZWROT NOWYCH USTAWIEŃ
    # ------------------------------------------------------

    def get_settings(self) -> dict:
        return {
            "alerts_enabled": bool(self.chk_alerts.isChecked()),
            "temp_min": float(self.spin_tmin.value()),
            "temp_max": float(self.spin_tmax.value()),
            "hum_min": float(self.spin_hmin.value()),
            "hum_max": float(self.spin_hmax.value()),
        }
