import sys
import os
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QColor, QFont, QIcon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import init_db, SessionLocal
from database.migrate import upgrade_database
from utils.data_init import init_sample_data
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("茶楼麻将房管理系统")
    app.setOrganizationName("MahjongManagement")

    app.setStyle("Fusion")

    splash = QSplashScreen()
    splash.setFixedSize(480, 320)
    pixmap = QPixmap(480, 320)
    pixmap.fill(QColor("#2c3e50"))
    from PySide6.QtGui import QPainter
    painter = QPainter(pixmap)
    painter.setPen(QColor("#ecf0f1"))
    font = QFont("Microsoft YaHei", 28, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "🀄 茶楼麻将房\n管理系统")
    font2 = QFont("Microsoft YaHei", 12)
    painter.setFont(font2)
    painter.setPen(QColor("#95a5a6"))
    painter.drawText(0, 280, 480, 30, Qt.AlignCenter, "正在初始化系统...")
    painter.end()
    splash.setPixmap(pixmap)
    splash.show()
    app.processEvents()

    try:
        init_db()
        splash.showMessage("正在初始化数据库...", Qt.AlignBottom | Qt.AlignCenter, QColor("#ecf0f1"))
        app.processEvents()

        upgrade_database()
        splash.showMessage("正在升级数据库...", Qt.AlignBottom | Qt.AlignCenter, QColor("#ecf0f1"))
        app.processEvents()

        db = SessionLocal()
        init_sample_data(db)
        db.close()
        splash.showMessage("正在加载示例数据...", Qt.AlignBottom | Qt.AlignCenter, QColor("#ecf0f1"))
        app.processEvents()

        QTimer.singleShot(1500, lambda: (splash.close(), show_main_window(app)))
    except Exception as e:
        splash.close()
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "系统错误", f"系统初始化失败：{str(e)}")
        sys.exit(1)

    sys.exit(app.exec())


def show_main_window(app: QApplication):
    db = SessionLocal()
    window = MainWindow(db)
    window.show()


if __name__ == "__main__":
    main()
