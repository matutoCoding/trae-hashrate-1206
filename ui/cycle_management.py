from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QTableWidgetItem,
                               QPushButton, QLabel, QGroupBox, QSplitter,
                               QComboBox, QDateEdit, QTimeEdit, QLineEdit,
                               QCheckBox, QTextEdit, QMessageBox, QDialog,
                               QInputDialog)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QColor, QBrush
from ui.base_widget import BaseWidget, BaseDialog
from modules.cycle_service import CycleService
from modules.table_service import TableService
from modules.booking_service import BookingService
from database.models import BookingStatus


class CycleRuleDialog(BaseDialog):
    WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    def __init__(self, parent=None, tables=None, rule_data=None):
        self.tables = tables or []
        self.rule_data = rule_data
        super().__init__("周期规则设置", parent)
        self.resize(500, 600)

    def init_dialog(self):
        self.edit_name = self.create_line_edit("如：张总每周固定场")
        self.edit_customer = self.create_line_edit("客人姓名")
        self.edit_phone = self.create_line_edit("联系电话")
        self.combo_table = self.create_combo([f"{t.table_number} - {t.name} (¥{t.hourly_rate}/时)" for t in self.tables])
        self.combo_weekday = self.create_combo(self.WEEKDAYS)
        self.time_start = self.create_time_edit()
        self.time_end = self.create_time_edit()
        self.time_end.setTime(QTime(22, 0))
        self.spin_people = self.create_spin(1, 20, " 人")
        self.date_start = self.create_date_edit()
        self.date_end = self.create_date_edit()
        self.date_end.setDate(QDate.currentDate().addMonths(3))
        self.chk_has_end = QCheckBox("设置结束日期")
        self.chk_has_end.setChecked(True)
        self.chk_has_end.toggled.connect(self.date_end.setEnabled)
        self.spin_repeat = self.create_spin(1, 52, " 周")
        self.chk_active = QCheckBox("启用此规则")
        self.chk_active.setChecked(True)
        self.edit_description = self.create_text_edit("备注信息")

        self.add_field("规则名称", self.edit_name, True)
        self.add_field("客人姓名", self.edit_customer, True)
        self.add_field("联系电话", self.edit_phone)
        self.add_field("麻将桌", self.combo_table, True)
        self.add_field("每周", self.combo_weekday, True)
        self.add_field("开始时间", self.time_start, True)
        self.add_field("结束时间", self.time_end, True)
        self.add_field("人数", self.spin_people)
        self.add_field("开始日期", self.date_start, True)

        end_layout = QHBoxLayout()
        end_layout.addWidget(self.chk_has_end)
        end_layout.addWidget(self.date_end)
        self.add_field("结束日期", end_layout)

        self.add_field("每隔", self.spin_repeat)
        self.add_field("状态", self.chk_active)
        self.add_field("备注", self.edit_description)

        if self.rule_data:
            self.edit_name.setText(self.rule_data.name)
            self.edit_customer.setText(self.rule_data.customer_name)
            self.edit_phone.setText(self.rule_data.customer_phone or "")
            for i, t in enumerate(self.tables):
                if t.id == self.rule_data.table_id:
                    self.combo_table.setCurrentIndex(i)
                    break
            self.combo_weekday.setCurrentIndex(self.rule_data.day_of_week - 1)
            self.time_start.setTime(QTime(self.rule_data.start_time.hour,
                                        self.rule_data.start_time.minute))
            self.time_end.setTime(QTime(self.rule_data.end_time.hour,
                                  self.rule_data.end_time.minute))
            self.spin_people.setValue(self.rule_data.people_count)
            self.date_start.setDate(QDate(self.rule_data.start_date.year,
                                        self.rule_data.start_date.month,
                                        self.rule_data.start_date.day))
            if self.rule_data.end_date:
                self.date_end.setDate(QDate(self.rule_data.end_date.year,
                                    self.rule_data.end_date.month,
                                    self.rule_data.end_date.day))
                self.chk_has_end.setChecked(True)
            else:
                self.chk_has_end.setChecked(False)
                self.date_end.setEnabled(False)
            self.spin_repeat.setValue(self.rule_data.repeat_weeks)
            self.chk_active.setChecked(self.rule_data.is_active)
            self.edit_description.setPlainText(self.rule_data.description or "")

    def get_data(self) -> dict:
        table_idx = self.combo_table.currentIndex()
        table = self.tables[table_idx] if table_idx >= 0 else None
        return {
            "name": self.edit_name.text().strip(),
            "customer_name": self.edit_customer.text().strip(),
            "customer_phone": self.edit_phone.text().strip() or None,
            "table_id": table.id if table else None,
            "day_of_week": self.combo_weekday.currentIndex() + 1,
            "start_time": self.time_start.time().toPython(),
            "end_time": self.time_end.time().toPython(),
            "people_count": self.spin_people.value(),
            "start_date": self.date_start.date().toPython(),
            "end_date": self.date_end.date().toPython() if self.chk_has_end.isChecked() else None,
            "repeat_weeks": self.spin_repeat.value(),
            "is_active": self.chk_active.isChecked(),
            "description": self.edit_description.toPlainText().strip() or None
        }

    def validate(self) -> bool:
        if not self.edit_name.text().strip():
            self.show_error("提示", "请输入规则名称")
            return False
        return True


class PreviewDialog(QDialog):
    def __init__(self, parent=None, bookings=None, conflicts=None):
        super().__init__(parent)
        self.setWindowTitle("生成预览")
        self.setModal(True)
        self.resize(600, 500)
        self.bookings = bookings or []
        self.conflicts = conflicts or []

        layout = QVBoxLayout(self)

        if self.conflicts:
            conflict_group = QGroupBox(f"⚠️ 时间冲突 ({len(self.conflicts)} 条)")
            conflict_layout = QVBoxLayout(conflict_group)
            conflict_text = QTextEdit()
            conflict_text.setReadOnly(True)
            conflict_text.setPlainText("\n".join(self.conflicts))
            conflict_text.setStyleSheet("color: #f44336;")
            conflict_layout.addWidget(conflict_text)
            layout.addWidget(conflict_group)

        booking_group = QGroupBox(f"📋 将生成以下预订 ({len(self.bookings)} 条)")
        booking_layout = QVBoxLayout(booking_group)
        from ui.base_widget import BaseWidget
        self.table = BaseWidget().create_table(["日期", "时间", "时长", "金额"])
        self.table.horizontalHeader().setStretchLastSection(True)
        booking_layout.addWidget(self.table)
        layout.addWidget(booking_group)

        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("确认生成")
        self.btn_cancel = QPushButton("取消")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(0)
        for b in self.bookings:
            row = self.table.rowCount()
            self.table.insertRow(row)
            time_str = f"{b.start_time.strftime('%H:%M')}-{b.end_time.strftime('%H:%M')}"
            for col, value in enumerate([
                str(b.booking_date), time_str, f"{b.total_hours:.1f}h", f"¥{b.base_amount}"]):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                self.table.setItem(row, col, item)


class CycleManagementWidget(BaseWidget):
    WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.cycle_service = CycleService(self.db)
        self.table_service = TableService(self.db)
        self.booking_service = BookingService(self.db)
        self.refresh()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("🔄 周期预订管理")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1976d2;")
        main_layout.addWidget(title)

        splitter = QSplitter(Qt.Vertical)

        rule_group = QGroupBox("周期规则列表")
        rule_layout = QVBoxLayout(rule_group)

        btn_layout = QHBoxLayout()
        self.btn_add = self.create_button("➕ 添加规则", callback=self.add_rule)
        self.btn_edit = self.create_button("✏️ 修改规则", callback=self.edit_rule)
        self.btn_delete = self.create_button("🗑️ 删除规则", callback=self.delete_rule)
        self.btn_preview = self.create_button("👁️ 预览生成", callback=self.preview_generate)
        self.btn_generate = self.create_button("⚡ 生成预订", callback=self.generate_bookings)
        self.btn_generate_all = self.create_button("🚀 生成全部", callback=self.generate_all)
        self.btn_refresh = self.create_button("🔄 刷新", callback=self.refresh)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_preview)
        btn_layout.addWidget(self.btn_generate)
        btn_layout.addWidget(self.btn_generate_all)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_refresh)
        rule_layout.addLayout(btn_layout)

        self.rule_widget = self.create_table([
            "ID", "规则名称", "客人", "桌号", "每周", "时间", "开始日期", "结束日期", "状态"
        ])
        rule_layout.addWidget(self.rule_widget)

        splitter.addWidget(rule_group)

        generated_group = QGroupBox("生成的预订")
        generated_layout = QVBoxLayout(generated_group)

        btn_gen_layout = QHBoxLayout()
        self.btn_edit_booking = self.create_button("✏️ 修改预订", callback=self.edit_generated_booking)
        self.btn_cancel_booking = self.create_button("❌ 取消预订", callback=self.cancel_generated_booking)
        btn_gen_layout.addWidget(self.btn_edit_booking)
        btn_gen_layout.addWidget(self.btn_cancel_booking)
        btn_gen_layout.addStretch()
        generated_layout.addLayout(btn_gen_layout)

        self.booking_widget = self.create_table([
            "ID", "桌号", "客人", "日期", "时间", "时长", "金额", "状态"
        ])
        generated_layout.addWidget(self.booking_widget)

        splitter.addWidget(generated_group)
        splitter.setSizes([350, 350])
        main_layout.addWidget(splitter)

        self.rule_widget.itemSelectionChanged.connect(self.on_rule_selected)

    def refresh(self):
        self.refresh_rules()
        self.refresh_generated_bookings()

    def refresh_rules(self):
        self.clear_table(self.rule_widget)
        rules = self.cycle_service.get_all_cycle_rules()
        for rule in rules:
            row = self.rule_widget.rowCount()
            self.rule_widget.insertRow(row)
            weekday = self.WEEKDAYS[rule.day_of_week - 1] if 1 <= rule.day_of_week <= 7 else str(rule.day_of_week)
            time_str = f"{rule.start_time.strftime('%H:%M')}-{rule.end_time.strftime('%H:%M')}"
            status = "启用" if rule.is_active else "停用"
            end_date = rule.end_date or "长期"
            self.set_table_row(self.rule_widget, row, [
                rule.id, rule.name, rule.customer_name,
                rule.table.table_number if rule.table else "",
                weekday, time_str,
                rule.start_date, end_date, status
            ])
            status_item = self.rule_widget.item(row, 8)
            status_item.setForeground(QBrush(QColor("#4caf50" if rule.is_active else "#9e9e9e")))

    def on_rule_selected(self):
        self.refresh_generated_bookings()

    def refresh_generated_bookings(self):
        self.clear_table(self.booking_widget)
        rule_id = self.get_selected_rule_id()
        if not rule_id:
            return
        bookings = self.booking_service.get_bookings_by_cycle(rule_id)
        for booking in bookings:
            row = self.booking_widget.rowCount()
            self.booking_widget.insertRow(row)
            time_str = f"{booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}"
            self.set_table_row(self.booking_widget, row, [
                booking.id,
                booking.table.table_number if booking.table else "",
                booking.customer_name, booking.booking_date, time_str,
                f"{booking.total_hours:.1f}h", f"¥{booking.base_amount}",
                booking.status.value
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

    def get_selected_rule_id(self):
        row = self.rule_widget.currentRow()
        if row >= 0:
            return int(self.rule_widget.item(row, 0).text())
        return None

    def get_selected_booking_id(self):
        row = self.booking_widget.currentRow()
        if row >= 0:
            return int(self.booking_widget.item(row, 0).text())
        return None

    def add_rule(self):
        tables = self.table_service.get_all_tables()
        if not tables:
            self.show_info("提示", "请先添加麻将桌")
            return
        dialog = CycleRuleDialog(self, tables)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.cycle_service.create_cycle_rule(**data)
                self.show_info("成功", "周期规则创建成功")
                self.refresh_rules()
            except Exception as e:
                self.show_error("错误", str(e))

    def edit_rule(self):
        rule_id = self.get_selected_rule_id()
        if not rule_id:
            self.show_info("提示", "请选择要修改的规则")
            return
        rule = self.cycle_service.get_cycle_rule(rule_id)
        tables = self.table_service.get_all_tables()
        dialog = CycleRuleDialog(self, tables, rule)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.cycle_service.update_cycle_rule(rule_id, **data)
                self.show_info("成功", "周期规则修改成功")
                self.refresh_rules()
            except Exception as e:
                self.show_error("错误", str(e))

    def delete_rule(self):
        rule_id = self.get_selected_rule_id()
        if not rule_id:
            self.show_info("提示", "请选择要删除的规则")
            return

        choice, ok = QInputDialog.getItem(self, "删除确认",
                                            "是否同时删除已生成的预订？",
                                            ["仅删除规则", "删除规则和已生成的预订"],
                                            0, False)
        if ok:
            delete_generated = choice == "删除规则和已生成的预订"
            if self.cycle_service.delete_cycle_rule(rule_id, delete_generated):
                self.show_info("成功", "周期规则删除成功")
                self.refresh()
            else:
                self.show_error("错误", "删除失败")

    def preview_generate(self):
        rule_id = self.get_selected_rule_id()
        if not rule_id:
            self.show_info("提示", "请选择要预览的规则")
            return
        bookings, conflicts = self.cycle_service.preview_generated_bookings(rule_id)
        if not bookings and not conflicts:
            self.show_info("提示", "没有可生成的预订")
            return
        dialog = PreviewDialog(self, bookings, conflicts)
        if dialog.exec() == QDialog.Accepted:
            count, messages = self.cycle_service.generate_bookings(rule_id, skip_conflicts=True)
            msg = "\n".join(messages)
            self.show_info("生成结果", msg)
            self.refresh()

    def generate_bookings(self):
        rule_id = self.get_selected_rule_id()
        if not rule_id:
            self.show_info("提示", "请选择要生成的规则")
            return
        count, messages = self.cycle_service.generate_bookings(rule_id, skip_conflicts=True)
        msg = "\n".join(messages)
        self.show_info("生成结果", msg)
        self.refresh()

    def generate_all(self):
        if self.show_confirm("确认", "确定要生成所有启用的周期规则的预订吗？"):
            count, messages = self.cycle_service.generate_all_active_cycles()
            msg = "\n".join(messages) if messages else f"共生成 {count} 条预订"
            self.show_info("生成结果", msg)
            self.refresh()

    def edit_generated_booking(self):
        booking_id = self.get_selected_booking_id()
        if not booking_id:
            self.show_info("提示", "请选择要修改的预订")
            return
        booking = self.booking_service.get_booking(booking_id)
        from ui.table_management import BookingDialog
        tables = self.table_service.get_all_tables()
        dialog = BookingDialog(self, tables, booking)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.booking_service.update_booking(booking_id, **data)
                self.show_info("成功", "预订修改成功")
                self.refresh_generated_bookings()
            except Exception as e:
                self.show_error("错误", str(e))

    def cancel_generated_booking(self):
        booking_id = self.get_selected_booking_id()
        if not booking_id:
            self.show_info("提示", "请选择要取消的预订")
            return
        if self.show_confirm("确认", "确定要取消这个预订吗？"):
            if self.booking_service.cancel_booking(booking_id):
                self.show_info("成功", "预订已取消")
                self.refresh_generated_bookings()
            else:
                self.show_error("错误", "取消失败")
