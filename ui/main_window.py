from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QListWidget, QListWidgetItem, QStackedWidget,
                               QLabel, QFrame, QSplitter)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QColor
from sqlalchemy.orm import Session
from database.db import SessionLocal
from ui.table_management import TableManagementWidget
from ui.cycle_management import CycleManagementWidget
from ui.discount_management import DiscountManagementWidget
from ui.billing import BillingWidget
from ui.inspection_management import InspectionManagementWidget


class MainWindow(QMainWindow):
    def __init__(self, db: Session = None):
        super().__init__()
        self.db = db or SessionLocal()
        self.setWindowTitle("茶楼麻将房管理系统")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.create_sidebar())
        splitter.addWidget(self.create_content())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 1080])
        main_layout.addWidget(splitter)

        self.create_status_bar()

    def create_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-right: 1px solid #34495e;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 10px 0;
            }
            QListWidget::item {
                padding: 14px 20px;
                color: #ecf0f1;
                font-size: 14px;
                border-left: 4px solid transparent;
            }
            QListWidget::item:hover {
                background-color: #34495e;
            }
            QListWidget::item:selected {
                background-color: #1abc9c;
                color: white;
                border-left: 4px solid #16a085;
            }
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        logo_label = QLabel("🀄 麻将房管理")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 20px 0;
                background-color: #1a252f;
                border-bottom: 1px solid #34495e;
            }
        """)
        sidebar_layout.addWidget(logo_label)

        self.nav_list = QListWidget()
        self.nav_list.setSpacing(2)
        self.nav_list.setIconSize(QSize(20, 20))

        menu_items = [
            ("🎲 麻将桌排期", "麻将桌建档、预订管理、入住退房"),
            ("📅 周期预订", "周期规则设定、批量生成预订"),
            ("🎁 优惠管理", "优惠券管理、计算规则配置"),
            ("💰 账单管理", "账单生成、支付、打印"),
            ("🔧 设备点检", "麻将机点检、维修管理"),
        ]

        for idx, (text, tooltip) in enumerate(menu_items):
            item = QListWidgetItem(text)
            item.setToolTip(tooltip)
            item.setTextAlignment(Qt.AlignVCenter)
            self.nav_list.addItem(item)

        self.nav_list.currentRowChanged.connect(self.switch_page)
        sidebar_layout.addWidget(self.nav_list)
        sidebar_layout.addStretch()

        version_label = QLabel("v1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 12px;
                padding: 10px;
            }
        """)
        sidebar_layout.addWidget(version_label)

        return sidebar

    def create_content(self) -> QWidget:
        content = QFrame()
        content.setStyleSheet("""
            QFrame {
                background-color: #f5f6fa;
            }
        """)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 1px solid #e0e0e0;
            }
        """)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        self.page_title = QLabel("麻将桌排期")
        self.page_title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        header_layout.addWidget(self.page_title)
        header_layout.addStretch()

        self.page_subtitle = QLabel("麻将桌建档、预订管理、入住退房")
        self.page_subtitle.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #7f8c8d;
            }
        """)
        header_layout.addWidget(self.page_subtitle)

        content_layout.addWidget(header)

        self.stacked_widget = QStackedWidget()

        self.table_widget = TableManagementWidget(self.db)
        self.cycle_widget = CycleManagementWidget(self.db)
        self.discount_widget = DiscountManagementWidget(self.db)
        self.billing_widget = BillingWidget(self.db)
        self.inspection_widget = InspectionManagementWidget(self.db)

        self.stacked_widget.addWidget(self.table_widget)
        self.stacked_widget.addWidget(self.cycle_widget)
        self.stacked_widget.addWidget(self.discount_widget)
        self.stacked_widget.addWidget(self.billing_widget)
        self.stacked_widget.addWidget(self.inspection_widget)

        content_layout.addWidget(self.stacked_widget)

        self.nav_list.setCurrentRow(0)

        return content

    def switch_page(self, index: int):
        self.stacked_widget.setCurrentIndex(index)

        page_titles = [
            ("麻将桌排期", "麻将桌建档、预订管理、入住退房"),
            ("周期预订", "周期规则设定、批量生成预订"),
            ("优惠管理", "优惠券管理、计算规则配置"),
            ("账单管理", "账单生成、支付、打印"),
            ("设备点检", "麻将机点检、维修管理"),
        ]

        if 0 <= index < len(page_titles):
            title, subtitle = page_titles[index]
            self.page_title.setText(title)
            self.page_subtitle.setText(subtitle)

            current_widget = self.stacked_widget.currentWidget()
            if hasattr(current_widget, 'refresh'):
                current_widget.refresh()

    def create_status_bar(self):
        status_bar = self.statusBar()
        status_bar.showMessage("系统就绪")
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: white;
                border-top: 1px solid #e0e0e0;
                color: #7f8c8d;
            }
        """)

    def closeEvent(self, event):
        if self.db:
            self.db.close()
        event.accept()
