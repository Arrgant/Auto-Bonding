"""Dialog for entering layer or entity thickness values."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class LayerThicknessDialog(QDialog):
    """Collect a thickness value with optional quick presets."""

    QUICK_VALUES = (0.1, 0.2, 0.3, 0.5)

    def __init__(
        self,
        *,
        title: str,
        headline: str,
        detail: str | None,
        current_value: float,
        apply_to_remaining_label: str | None = None,
        reject_text: str = "Cancel",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(420, 240)

        self._clear_requested = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        headline_label = QLabel(headline, self)
        headline_label.setWordWrap(True)
        headline_label.setObjectName("SectionTitle")
        layout.addWidget(headline_label)

        if detail:
            detail_label = QLabel(detail, self)
            detail_label.setWordWrap(True)
            detail_label.setObjectName("MutedLabel")
            layout.addWidget(detail_label)

        input_row = QGridLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setHorizontalSpacing(10)
        input_row.setVerticalSpacing(8)

        value_label = QLabel("Thickness", self)
        input_row.addWidget(value_label, 0, 0)

        self.spinbox = QDoubleSpinBox(self)
        self.spinbox.setDecimals(3)
        self.spinbox.setRange(0.0, 50.0)
        self.spinbox.setSingleStep(0.05)
        self.spinbox.setSuffix(" mm")
        self.spinbox.setValue(current_value)
        self.spinbox.setAccelerated(True)
        input_row.addWidget(self.spinbox, 0, 1)

        quick_label = QLabel("Quick values", self)
        input_row.addWidget(quick_label, 1, 0, alignment=Qt.AlignmentFlag.AlignTop)

        quick_row = QHBoxLayout()
        quick_row.setContentsMargins(0, 0, 0, 0)
        quick_row.setSpacing(6)
        for value in self.QUICK_VALUES:
            button = QPushButton(f"{value:.3f}", self)
            button.clicked.connect(lambda _checked=False, preset=value: self.spinbox.setValue(preset))
            quick_row.addWidget(button)
        quick_row.addStretch(1)
        input_row.addLayout(quick_row, 1, 1)

        layout.addLayout(input_row)

        self.apply_to_remaining_checkbox: QCheckBox | None = None
        if apply_to_remaining_label is not None:
            self.apply_to_remaining_checkbox = QCheckBox(apply_to_remaining_label, self)
            layout.addWidget(self.apply_to_remaining_checkbox)

        button_box = QDialogButtonBox(self)
        self.apply_button = button_box.addButton("Apply", QDialogButtonBox.ButtonRole.AcceptRole)
        self.clear_button = button_box.addButton("Clear", QDialogButtonBox.ButtonRole.ActionRole)
        self.reject_button = button_box.addButton(reject_text, QDialogButtonBox.ButtonRole.RejectRole)
        self.apply_button.clicked.connect(self.accept)
        self.clear_button.clicked.connect(self._accept_clear)
        self.reject_button.clicked.connect(self.reject)
        layout.addWidget(button_box)

    def showEvent(self, event) -> None:  # pragma: no cover - GUI focus behavior
        super().showEvent(event)
        self.spinbox.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        line_edit = self.spinbox.lineEdit()
        if line_edit is not None:
            line_edit.selectAll()

    def result_payload(self) -> dict[str, float | bool]:
        thickness = 0.0 if self._clear_requested else float(self.spinbox.value())
        return {
            "thickness": thickness,
            "clear": self._clear_requested,
            "apply_to_remaining": bool(
                self.apply_to_remaining_checkbox is not None
                and self.apply_to_remaining_checkbox.isChecked()
            ),
        }

    def _accept_clear(self) -> None:
        self._clear_requested = True
        self.accept()


__all__ = ["LayerThicknessDialog"]
