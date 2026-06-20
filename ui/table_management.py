from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QTableWidgetItem,
                               QPushButton, QLabel, QGroupBox, QSplitter,
                               QComboBox, QDateEdit, QTimeEdit, QLineEdit,
                               QMessageBox)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QColor, QBrush
from ui.base_widget import BaseWidget, BaseDialog
from modules.table_service import TableService
from modules.booking_service import BookingService
from database.models import TableStatus, BookingStatus
from datetime import date, time


class TableDialog(BaseDialog):
    def __init__(self, parent=None, table_data=None):
        self.table_data = table_data
        super().__init__("麻将桌信息", parent)
        self.resize(450, 500)

    def init_dialog(self):
        self.edit_number = self.create_line_edit("如：A01")
        self.edit_name = self.create_line_edit("如：豪华包厢1")
        self.combo_room_type = self.create_combo(["普通厅", "标准间", "豪华包厢", "VIP包厢"])
        self.spin_hourly_rate = self.create_double_spin(0, 1000, 2, " 元/小时")
        self.spin_min_hours = self.create_double_spin(0.5, 24, 1, " 小时")
        self.spin_max_people = self.create_spin(2, 10, " 人")
        self.edit_machine_model = self.create_line_edit("如：雀友T380")
        self.date_purchase = self.create_date_edit()
        self.combo_status = self.create_combo([s.value for s in TableStatus])
        self.edit_location = self.create_line_edit("如：二楼、大厅")
        self.edit_description = self.create_text_edit("备注信息")

        self.add_field("桌号", self.edit_number, True)
        self.add_field("名称", self.edit_name)
        self.add_field("房间类型", self.combo_room_type)
        self.add_field("小时单价", self.spin_hourly_rate, True)
        self.add_field("最低时长", self.spin_min_hours)
        self.add_field("容纳人数", self.spin_max_people)
        self.add_field("麻将机型号", self.edit_machine_model)
        self.add_field("购买日期", self.date_purchase)
        self.add_field("状态", self.combo_status)
        self.add_field("位置", self.edit_location)
        self.add_field("备注", self.edit_description)

        if self.table_data:
            self.edit_number.setText(self.table_data.table_number)
            self.edit_name.setText(self.table_data.name or "")
            if self.table_data.room_type:
                idx = self.combo_room_type.findText(self.table_data.room_type)
                if idx >= 0:
                    self.combo_room_type.setCurrentIndex(idx)
            self.spin_hourly_rate.setValue(self.table_data.hourly_rate)
            self.spin_min_hours.setValue(self.table_data.minimum_hours)
            self.spin_max_people.setValue(self.table_data.max_people)
            self.edit_machine_model.setText(self.table_data.machine_model or "")
            if self.table_data.purchase_date:
                self.date_purchase.setDate(QDate(self.table_data.purchase_date.year,
                                                  self.table_data.purchase_date.month,
                                                  self.table_data.purchase_date.day))
            if self.table_data.status:
                idx = self.combo_status.findText(self.table_data.status.value)
                if idx >= 0:
                    self.combo_status.setCurrentIndex(idx)
            self.edit_location.setText(self.table_data.location or "")
            self.edit_description.setPlainText(self.table_data.description or "")

    def get_data(self) -> dict:
        return {
            "table_number": self.edit_number.text().strip(),
            "name": self.edit_name.text().strip() or self.edit_number.text().strip(),
            "room_type": self.combo_room_type.currentText(),
            "hourly_rate": self.spin_hourly_rate.value(),
            "minimum_hours": self.spin_min_hours.value(),
            "max_people": self.spin_max_people.value(),
            "machine_model": self.edit_machine_model.text().strip() or None,
            "purchase_date": self.date_purchase.date().toPython() if self.date_purchase.date() else None,
            "status": TableStatus(self.combo_status.currentText()),
            "location": self.edit_location.text().strip() or None,
            "description": self.edit_description.toPlainText().strip() or None
        }

    def validate(self) -> bool:
        if not self.edit_number.text().strip():
            self.show_error("提示", "请输入桌号")
            return False
        if self.spin_hourly_rate.value() <= 0:
            self.show_error("提示", "小时单价必须大于0")
            return False
        return True


class BookingDialog(BaseDialog):
    def __init__(self, parent=None, tables=None, booking_data=None):
        self.tables = tables or []
        self.booking_data = booking_data
        super().__init__("预订信息", parent)
        self.resize(450, 550)

    def init_dialog(self):
        self.combo_table = self.create_combo([f"{t.table_number} - {t.name} (¥{t.hourly_rate}/时)" for t in self.tables])
        self.edit_customer = self.create_line_edit("客人姓名")
        self.edit_phone = self.create_line_edit("联系电话")
        self.date_booking = self.create_date_edit()
        self.time_start = self.create_time_edit()
        self.time_end = self.create_time_edit()
        self.time_end.setTime(QTime(22, 0))
        self.spin_people = self.create_spin(1, 20, " 人")
        self.combo_status = self.create_combo([s.value for s in BookingStatus])
        self.edit_note = self.create_text_edit("备注信息")

        self.add_field("麻将桌", self.combo_table, True)
        self.add_field("客人姓名", self.edit_customer, True)
        self.add_field("联系电话", self.edit_phone)
        self.add_field("预订日期", self.date_booking, True)
        self.add_field("开始时间", self.time_start, True)
        self.add_field("结束时间", self.time_end, True)
        self.add_field("人数", self.spin_people)
        self.add_field("状态", self.combo_status)
        self.add_field("备注", self.edit_note)

        if self.booking_data:
            for i, t in enumerate(self.tables):
                if t.id == self.booking_data.table_id:
                    self.combo_table.setCurrentIndex(i)
                    break
            self.edit_customer.setText(self.booking_data.customer_name)
            self.edit_phone.setText(self.booking_data.customer_phone or "")
            self.date_booking.setDate(QDate(self.booking_data.booking_date.year,
                                            self.booking_data.booking_date.month,
                                            self.booking_data.booking_date.day))
            self.time_start.setTime(QTime(self.booking_data.start_time.hour,
                                          self.booking_data.start_time.minute))
            self.time_end.setTime(QTime(self.booking_data.end_time.hour,
                                        self.booking_data.end_time.minute))
            self.spin_people.setValue(self.booking_data.people_count)
            if self.booking_data.status:
                idx = self.combo_status.findText(self.booking_data.status.value)
                if idx >= 0:
                    self.combo_status.setCurrentIndex(idx)
            self.edit_note.setPlainText(self.booking_data.note or "")

    def get_data(self) -> dict:
        table_idx = self.combo_table.currentIndex()
        table = self.tables[table_idx] if table_idx >= 0 else None
        return {
            "table_id": table.id if table else None,
            "customer_name": self.edit_customer.text().strip(),
            "customer_phone": self.edit_phone.text().strip() or None,
            "booking_date": self.date_booking.date().toPython(),
            "start_time": self.time_start.time().toPython(),
            "end_time": self.time_end.time().toPython(),
            "people_count": self.spin_people.value(),
            "status": BookingStatus(self.combo_status.currentText()),
            "note": self.edit_note.toPlainText().strip() or None
        }

    def validate(self) -> bool:
        if not self.edit_customer.text().strip():
            self.show_error("提示", "请输入客人姓名")
            return False
        if self.combo_table.currentIndex() < 0:
            self.show_error("提示", "请选择麻将桌")
            return False
        start = self.time_start.time().toPython()
        end = self.time_end.time().toPython()
        if start >= end:
            self.show_error("提示", "结束时间必须晚于开始时间")
            return False
        return True


class TableManagementWidget(BaseWidget):
    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.table_service = TableService(self.db)
        self.booking_service = BookingService(self.db)
        self.refresh()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("🀄 麻将桌排期管理")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1976d2;")
        main_layout.addWidget(title)

        splitter = QSplitter(Qt.Vertical)

        table_group = QGroupBox("麻将桌列表")
        table_layout = QVBoxLayout(table_group)

        btn_layout = QHBoxLayout()
        self.btn_add_table = self.create_button("➕ 添加麻将桌", callback=self.add_table)
        self.btn_edit_table = self.create_button("✏️ 修改麻将桌", callback=self.edit_table)
        self.btn_delete_table = self.create_button("🗑️ 删除麻将桌", callback=self.delete_table)
        self.btn_refresh = self.create_button("🔄 刷新", callback=self.refresh)
        btn_layout.addWidget(self.btn_add_table)
        btn_layout.addWidget(self.btn_edit_table)
        btn_layout.addWidget(self.btn_delete_table)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_refresh)
        table_layout.addLayout(btn_layout)

        self.table_widget = self.create_table([
            "ID", "桌号", "名称", "类型", "单价", "状态", "位置", "麻将机型号"
        ])
        table_layout.addWidget(self.table_widget)

        splitter.addWidget(table_group)

        booking_group = QGroupBox("今日预订")
        booking_layout = QVBoxLayout(booking_group)

        btn_booking_layout = QHBoxLayout()
        self.btn_add_booking = self.create_button("➕ 新增预订", callback=self.add_booking)
        self.btn_edit_booking = self.create_button("✏️ 修改预订", callback=self.edit_booking)
        self.btn_cancel_booking = self.create_button("❌ 取消预订", callback=self.cancel_booking)
        self.btn_checkin = self.create_button("✅ 入住", callback=self.checkin)
        self.btn_checkout = self.create_button("💰 结账", callback=self.checkout)
        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDisplayFormat("yyyy-MM-dd")
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.dateChanged.connect(self.refresh)
        btn_booking_layout.addWidget(self.btn_add_booking)
        btn_booking_layout.addWidget(self.btn_edit_booking)
        btn_booking_layout.addWidget(self.btn_cancel_booking)
        btn_booking_layout.addWidget(self.btn_checkin)
        btn_booking_layout.addWidget(self.btn_checkout)
        btn_booking_layout.addStretch()
        btn_booking_layout.addWidget(QLabel("日期:"))
        btn_booking_layout.addWidget(self.date_filter)
        booking_layout.addLayout(btn_booking_layout)

        self.booking_widget = self.create_table([
            "ID", "桌号", "客人", "日期", "时间", "时长", "金额", "状态", "来源"
        ])
        booking_layout.addWidget(self.booking_widget)

        splitter.addWidget(booking_group)
        splitter.setSizes([300, 400])
        main_layout.addWidget(splitter)

    def refresh(self):
        self.refresh_tables()
        self.refresh_bookings()

    def refresh_tables(self):
        self.clear_table(self.table_widget)
        tables = self.table_service.get_all_tables()
        for table in tables:
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)
            self.set_table_row(self.table_widget, row, [
                table.id, table.table_number, table.name, table.room_type,
                f"¥{table.hourly_rate}", table.status.value, table.location or "",
                table.machine_model or ""
            ])
            status_item = self.table_widget.item(row, 5)
            if table.status == TableStatus.IDLE:
                status_item.setForeground(QBrush(QColor("#4caf50")))
            elif table.status == TableStatus.OCCUPIED:
                status_item.setForeground(QBrush(QColor("#f44336")))
            elif table.status == TableStatus.RESERVED:
                status_item.setForeground(QBrush(QColor("#ff9800")))
            elif table.status == TableStatus.MAINTENANCE:
                status_item.setForeground(QBrush(QColor("#9e9e9e")))

    def refresh_bookings(self):
        self.clear_table(self.booking_widget)
        booking_date = self.date_filter.date().toPython()
        bookings = self.booking_service.get_bookings_by_date(booking_date)
        for booking in bookings:
            row = self.booking_widget.rowCount()
            self.booking_widget.insertRow(row)
            time_str = f"{booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}"
            source = "周期生成" if booking.is_from_cycle else "手动"
            self.set_table_row(self.booking_widget, row, [
                booking.id, booking.table.table_number if booking.table else "",
                booking.customer_name, booking.booking_date, time_str,
                f"{booking.total_hours:.1f}h", f"¥{booking.base_amount}",
                booking.status.value, source
            ])
            status_item = self.booking_widget.item(row, 7)
            if booking.status == BookingStatus.CONFIRMED:
                status_item.setForeground(QBrush(QColor("#4caf50")))
            elif booking.status == BookingStatus.IN_PROGRESS:
                status_item.setForeground(QBrush(QColor("#f44336")))
            elif booking.status == BookingStatus.COMPLETED:
                status_item.setForeground(QBrush(QColor("#2196f3")))
            elif booking.status == BookingStatus.CANCELLED:
                status_item.setForeground(QBrush(QColor("#9e9e9e")))

    def get_selected_table_id(self):
        row = self.table_widget.currentRow()
        if row >= 0:
            return int(self.table_widget.item(row, 0).text())
        return None

    def get_selected_booking_id(self):
        row = self.booking_widget.currentRow()
        if row >= 0:
            return int(self.booking_widget.item(row, 0).text())
        return None

    def add_table(self):
        dialog = TableDialog(self)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.table_service.create_table(**data)
                self.show_info("成功", "麻将桌创建成功")
                self.refresh_tables()
            except Exception as e:
                self.show_error("错误", str(e))

    def edit_table(self):
        table_id = self.get_selected_table_id()
        if not table_id:
            self.show_info("提示", "请选择要修改的麻将桌")
            return
        table = self.table_service.get_table(table_id)
        dialog = TableDialog(self, table)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.table_service.update_table(table_id, **data)
                self.show_info("成功", "麻将桌修改成功")
                self.refresh_tables()
            except Exception as e:
                self.show_error("错误", str(e))

    def delete_table(self):
        table_id = self.get_selected_table_id()
        if not table_id:
            self.show_info("提示", "请选择要删除的麻将桌")
            return
        if self.show_confirm("确认", "确定要删除这个麻将桌吗？相关预订也会受到影响。"):
            if self.table_service.delete_table(table_id):
                self.show_info("成功", "麻将桌删除成功")
                self.refresh_tables()
            else:
                self.show_error("错误", "删除失败")

    def add_booking(self):
        tables = self.table_service.get_all_tables()
        if not tables:
            self.show_info("提示", "请先添加麻将桌")
            return
        dialog = BookingDialog(self, tables)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.booking_service.create_booking(**data)
                self.show_info("成功", "预订创建成功")
                self.refresh_bookings()
            except Exception as e:
                self.show_error("错误", str(e))

    def edit_booking(self):
        booking_id = self.get_selected_booking_id()
        if not booking_id:
            self.show_info("提示", "请选择要修改的预订")
            return
        booking = self.booking_service.get_booking(booking_id)
        tables = self.table_service.get_all_tables()
        dialog = BookingDialog(self, tables, booking)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.booking_service.update_booking(booking_id, **data)
                self.show_info("成功", "预订修改成功")
                self.refresh_bookings()
            except Exception as e:
                self.show_error("错误", str(e))

    def cancel_booking(self):
        booking_id = self.get_selected_booking_id()
        if not booking_id:
            self.show_info("提示", "请选择要取消的预订")
            return
        if self.show_confirm("确认", "确定要取消这个预订吗？"):
            if self.booking_service.cancel_booking(booking_id):
                self.show_info("成功", "预订已取消")
                self.refresh_bookings()
            else:
                self.show_error("错误", "取消失败")

    def checkin(self):
        booking_id = self.get_selected_booking_id()
        if not booking_id:
            self.show_info("提示", "请选择要入住的预订")
            return
        booking = self.booking_service.get_booking(booking_id)
        if booking and booking.status != BookingStatus.CONFIRMED:
            self.show_error("错误", "只有已确认的预订才能入住")
            return
        if self.booking_service.check_in(booking_id):
            self.show_info("成功", "已入住")
            self.refresh()
        else:
            self.show_error("错误", "入住失败")

    def checkout(self):
        booking_id = self.get_selected_booking_id()
        if not booking_id:
            self.show_info("提示", "请选择要结账的预订")
            return
        booking = self.booking_service.get_booking(booking_id)
        if booking and booking.bill and booking.bill.is_paid:
            self.show_info("提示", "该预订已结账")
            return

        from ui.billing import BillingDialog
        tables = self.table_service.get_all_tables()
        dialog = BillingDialog(self, self.db, booking)
        if dialog.exec():
            self.refresh()
