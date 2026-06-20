from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QPushButton, QDialog, QFormLayout,
                               QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox,
                               QDateEdit, QTimeEdit, QTextEdit, QMessageBox,
                               QHeaderView, QLabel, QGroupBox, QSplitter)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QFont, QColor, QBrush
from sqlalchemy.orm import Session
from database.db import SessionLocal


class BaseWidget(QWidget):
    def __init__(self, db: Session = None, parent=None):
        super().__init__(parent)
        self.db = db or SessionLocal()
        self.init_ui()

    def init_ui(self):
        pass

    def refresh(self):
        pass

    def show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str):
        QMessageBox.information(self, title, message)

    def show_confirm(self, title: str, message: str) -> bool:
        reply = QMessageBox.question(self, title, message,
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        return reply == QMessageBox.Yes

    def create_button(self, text: str, icon=None, callback=None) -> QPushButton:
        btn = QPushButton(text)
        if icon:
            btn.setIcon(icon)
        if callback:
            btn.clicked.connect(callback)
        btn.setMinimumHeight(32)
        return btn

    def create_table(self, headers: list) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget {
                font-size: 12px;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 6px;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #cccccc;
            }
            QTableWidget::item:selected {
                background-color: #1976d2;
                color: white;
            }
        """)
        return table

    def set_table_row(self, table: QTableWidget, row: int, values: list):
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value) if value is not None else "")
            if isinstance(value, (int, float)):
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            table.setItem(row, col, item)

    def clear_table(self, table: QTableWidget):
        table.setRowCount(0)

    def add_table_row(self, table: QTableWidget, values: list):
        row = table.rowCount()
        table.insertRow(row)
        self.set_table_row(table, row, values)

    def create_double_spin(self, min_val: float = 0, max_val: float = 10000,
                           decimals: int = 2, suffix: str = "") -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setDecimals(decimals)
        spin.setSuffix(suffix)
        spin.setMinimumHeight(32)
        return spin

    def create_spin(self, min_val: int = 0, max_val: int = 10000,
                    suffix: str = "") -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSuffix(suffix)
        spin.setMinimumHeight(32)
        return spin

    def create_combo(self, items: list) -> QComboBox:
        combo = QComboBox()
        combo.addItems(items)
        combo.setMinimumHeight(32)
        return combo

    def create_date_edit(self) -> QDateEdit:
        edit = QDateEdit()
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("yyyy-MM-dd")
        edit.setDate(QDate.currentDate())
        edit.setMinimumHeight(32)
        return edit

    def create_time_edit(self) -> QTimeEdit:
        edit = QTimeEdit()
        edit.setDisplayFormat("HH:mm")
        edit.setMinimumHeight(32)
        return edit

    def create_line_edit(self, placeholder: str = "") -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(32)
        return edit

    def create_text_edit(self, placeholder: str = "") -> QTextEdit:
        edit = QTextEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(80)
        return edit


class BaseDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self.form_layout = QFormLayout()
        self.init_dialog()
        self.button_layout = QHBoxLayout()
        self.btn_ok = QPushButton("确定")
        self.btn_cancel = QPushButton("取消")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.btn_ok)
        self.button_layout.addWidget(self.btn_cancel)
        main_layout = QVBoxLayout()
        main_layout.addLayout(self.form_layout)
        main_layout.addLayout(self.button_layout)
        self.setLayout(main_layout)

    def init_dialog(self):
        pass

    def add_field(self, label: str, widget, required: bool = False):
        lbl = QLabel(label + (" *" if required else ""))
        self.form_layout.addRow(lbl, widget)

    def create_line_edit(self, placeholder: str = "") -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(32)
        return edit

    def create_double_spin(self, min_val: float = 0, max_val: float = 10000,
                           decimals: int = 2, suffix: str = "") -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setDecimals(decimals)
        spin.setSuffix(suffix)
        spin.setMinimumHeight(32)
        return spin

    def create_spin(self, min_val: int = 0, max_val: int = 10000,
                    suffix: str = "") -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSuffix(suffix)
        spin.setMinimumHeight(32)
        return spin

    def create_combo(self, items: list) -> QComboBox:
        combo = QComboBox()
        combo.addItems(items)
        combo.setMinimumHeight(32)
        return combo

    def create_date_edit(self) -> QDateEdit:
        edit = QDateEdit()
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("yyyy-MM-dd")
        edit.setDate(QDate.currentDate())
        edit.setMinimumHeight(32)
        return edit

    def create_time_edit(self) -> QTimeEdit:
        edit = QTimeEdit()
        edit.setDisplayFormat("HH:mm")
        edit.setMinimumHeight(32)
        return edit

    def create_text_edit(self, placeholder: str = "") -> QTextEdit:
        edit = QTextEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(80)
        return edit

    def get_data(self) -> dict:
        return {}

    def validate(self) -> bool:
        return True

    def accept(self):
        if self.validate():
            super().accept()
