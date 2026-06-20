from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QTableWidgetItem,
                               QPushButton, QLabel, QGroupBox, QSplitter,
                               QComboBox, QDateEdit, QLineEdit, QCheckBox,
                               QTextEdit, QDialog, QInputDialog)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush
from ui.base_widget import BaseWidget, BaseDialog
from modules.inspection_service import InspectionService
from modules.table_service import TableService
from database.models import InspectionStatus
from datetime import date


class InspectionDialog(BaseDialog):
    def __init__(self, parent=None, tables=None, inspection_data=None):
        self.tables = tables or []
        self.inspection_data = inspection_data
        super().__init__("麻将机点检", parent)
        self.resize(500, 650)

    def init_dialog(self):
        self.combo_table = self.create_combo([f"{t.table_number} - {t.name}" for t in self.tables])
        self.date_inspection = self.create_date_edit()
        self.edit_inspector = self.create_line_edit("点检人姓名")

        self.chk_tiles = QCheckBox("麻将牌齐全")
        self.chk_dice = QCheckBox("骰子正常")
        self.chk_power = QCheckBox("电源正常")
        self.chk_operation = QCheckBox("运行正常")
        self.chk_cleaning = QCheckBox("已清洁")

        for chk in [self.chk_tiles, self.chk_dice, self.chk_power, self.chk_operation, self.chk_cleaning]:
            chk.setStyleSheet("font-size: 13px;")

        self.edit_issues = self.create_text_edit("发现的问题")
        self.edit_actions = self.create_text_edit("处理措施")
        self.date_next = self.create_date_edit()
        self.date_next.setDate(QDate.currentDate().addDays(7))
        self.edit_remark = self.create_text_edit("备注")

        self.add_field("麻将桌", self.combo_table, True)
        self.add_field("点检日期", self.date_inspection, True)
        self.add_field("点检人", self.edit_inspector)

        check_group = QGroupBox("点检项目")
        check_layout = QVBoxLayout(check_group)
        check_layout.addWidget(self.chk_tiles)
        check_layout.addWidget(self.chk_dice)
        check_layout.addWidget(self.chk_power)
        check_layout.addWidget(self.chk_operation)
        check_layout.addWidget(self.chk_cleaning)
        self.form_layout.addRow(check_group)

        self.add_field("发现问题", self.edit_issues)
        self.add_field("处理措施", self.edit_actions)
        self.add_field("下次点检日期", self.date_next)
        self.add_field("备注", self.edit_remark)

        if self.inspection_data:
            for i, t in enumerate(self.tables):
                if t.id == self.inspection_data.table_id:
                    self.combo_table.setCurrentIndex(i)
                    break
            self.date_inspection.setDate(QDate(
                self.inspection_data.inspection_date.year,
                self.inspection_data.inspection_date.month,
                self.inspection_data.inspection_date.day
            ))
            self.edit_inspector.setText(self.inspection_data.inspector or "")
            self.chk_tiles.setChecked(self.inspection_data.tiles_complete or False)
            self.chk_dice.setChecked(self.inspection_data.dice_normal or False)
            self.chk_power.setChecked(self.inspection_data.power_supply_normal or False)
            self.chk_operation.setChecked(self.inspection_data.operation_normal or False)
            self.chk_cleaning.setChecked(self.inspection_data.cleaning_done or False)
            self.edit_issues.setPlainText(self.inspection_data.issues_found or "")
            self.edit_actions.setPlainText(self.inspection_data.actions_taken or "")
            if self.inspection_data.next_inspection_date:
                self.date_next.setDate(QDate(
                    self.inspection_data.next_inspection_date.year,
                    self.inspection_data.next_inspection_date.month,
                    self.inspection_data.next_inspection_date.day
                ))
            self.edit_remark.setPlainText(self.inspection_data.remark or "")

    def get_data(self) -> dict:
        table_idx = self.combo_table.currentIndex()
        table = self.tables[table_idx] if table_idx >= 0 else None
        return {
            "table_id": table.id if table else None,
            "inspection_date": self.date_inspection.date().toPython(),
            "inspector": self.edit_inspector.text().strip() or None,
            "tiles_complete": self.chk_tiles.isChecked(),
            "dice_normal": self.chk_dice.isChecked(),
            "power_supply_normal": self.chk_power.isChecked(),
            "operation_normal": self.chk_operation.isChecked(),
            "cleaning_done": self.chk_cleaning.isChecked(),
            "issues_found": self.edit_issues.toPlainText().strip() or None,
            "actions_taken": self.edit_actions.toPlainText().strip() or None,
            "next_inspection_date": self.date_next.date().toPython(),
            "remark": self.edit_remark.toPlainText().strip() or None
        }

    def validate(self) -> bool:
        if self.combo_table.currentIndex() < 0:
            self.show_error("提示", "请选择麻将桌")
            return False
        return True


class InspectionManagementWidget(BaseWidget):
    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.inspection_service = InspectionService(self.db)
        self.table_service = TableService(self.db)
        self.refresh()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("🔧 自动麻将机点检")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1976d2;")
        main_layout.addWidget(title)

        alert_group = QGroupBox("⚠️ 点检提醒")
        alert_layout = QVBoxLayout(alert_group)
        self.lbl_alert = QLabel("加载中...")
        self.lbl_alert.setStyleSheet("font-size: 13px; padding: 8px;")
        alert_layout.addWidget(self.lbl_alert)
        main_layout.addWidget(alert_group)

        splitter = QSplitter(Qt.Vertical)

        status_group = QGroupBox("麻将桌点检状态")
        status_layout = QVBoxLayout(status_group)

        btn_status_layout = QHBoxLayout()
        self.btn_batch_create = self.create_button("📋 批量创建本周点检", callback=self.batch_create)
        self.btn_refresh = self.create_button("🔄 刷新", callback=self.refresh)
        btn_status_layout.addWidget(self.btn_batch_create)
        btn_status_layout.addStretch()
        btn_status_layout.addWidget(self.btn_refresh)
        status_layout.addLayout(btn_status_layout)

        self.status_widget = self.create_table([
            "桌号", "名称", "位置", "上次点检", "距今天数", "下次点检", "状态"
        ])
        status_layout.addWidget(self.status_widget)

        splitter.addWidget(status_group)

        record_group = QGroupBox("点检记录")
        record_layout = QVBoxLayout(record_group)

        btn_record_layout = QHBoxLayout()
        self.btn_add = self.create_button("➕ 新增点检", callback=self.add_inspection)
        self.btn_edit = self.create_button("✏️ 修改点检", callback=self.edit_inspection)
        self.btn_complete = self.create_button("✅ 完成点检", callback=self.complete_inspection)
        self.btn_repair = self.create_button("🔧 标记维修", callback=self.mark_repaired)
        self.btn_delete = self.create_button("🗑️ 删除", callback=self.delete_inspection)
        btn_record_layout.addWidget(self.btn_add)
        btn_record_layout.addWidget(self.btn_edit)
        btn_record_layout.addWidget(self.btn_complete)
        btn_record_layout.addWidget(self.btn_repair)
        btn_record_layout.addWidget(self.btn_delete)
        btn_record_layout.addStretch()

        date_filter_layout = QHBoxLayout()
        date_filter_layout.addWidget(QLabel("日期:"))
        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDisplayFormat("yyyy-MM-dd")
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.dateChanged.connect(self.refresh_records)
        date_filter_layout.addWidget(self.date_filter)
        btn_record_layout.addLayout(date_filter_layout)
        record_layout.addLayout(btn_record_layout)

        self.record_widget = self.create_table([
            "ID", "桌号", "点检日期", "点检人", "状态", "牌齐全", "骰子", "电源", "运行", "清洁"
        ])
        record_layout.addWidget(self.record_widget)

        splitter.addWidget(record_group)

        detail_group = QGroupBox("点检详情")
        detail_layout = QVBoxLayout(detail_group)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)
        splitter.addWidget(detail_group)

        splitter.setSizes([250, 300, 150])
        main_layout.addWidget(splitter)

        self.record_widget.itemSelectionChanged.connect(self.on_record_selected)

    def refresh(self):
        self.refresh_status()
        self.refresh_records()
        self.refresh_alerts()

    def refresh_alerts(self):
        due_list = self.inspection_service.get_tables_needing_inspection()
        need_count = sum(1 for item in due_list if item["needs_inspection"])
        if need_count > 0:
            table_names = [item["table"].table_number for item in due_list if item["needs_inspection"]]
            self.lbl_alert.setText(
                f"⚠️ 有 {need_count} 台麻将机需要点检: {', '.join(table_names)}"
            )
            self.lbl_alert.setStyleSheet(
                "font-size: 13px; padding: 8px; background: #ffebee; color: #c62828; border-radius: 4px;"
            )
        else:
            self.lbl_alert.setText("✅ 所有麻将机点检状态正常")
            self.lbl_alert.setStyleSheet(
                "font-size: 13px; padding: 8px; background: #e8f5e9; color: #2e7d32; border-radius: 4px;"
            )

    def refresh_status(self):
        self.clear_table(self.status_widget)
        status_list = self.inspection_service.get_tables_needing_inspection()
        for item in status_list:
            row = self.status_widget.rowCount()
            self.status_widget.insertRow(row)

            table = item["table"]
            last_date = item["last_inspection"].inspection_date if item["last_inspection"] else "-"
            days_since = item["days_since"] if item["days_since"] is not None else "-"
            next_date = item["next_date"] if item["next_date"] else "-"
            status = "需点检" if item["needs_inspection"] else "正常"

            self.set_table_row(self.status_widget, row, [
                table.table_number, table.name, table.location or "-",
                str(last_date), str(days_since), str(next_date), status
            ])

            status_item = self.status_widget.item(row, 6)
            if item["needs_inspection"]:
                status_item.setForeground(QBrush(QColor("#f44336")))
            else:
                status_item.setForeground(QBrush(QColor("#4caf50")))

    def refresh_records(self):
        self.clear_table(self.record_widget)
        inspection_date = self.date_filter.date().toPython()
        records = self.inspection_service.get_inspections_by_date(inspection_date)

        for record in records:
            row = self.record_widget.rowCount()
            self.record_widget.insertRow(row)

            status = record.status.value if record.status else "-"
            tiles = "✓" if record.tiles_complete else "✗"
            dice = "✓" if record.dice_normal else "✗"
            power = "✓" if record.power_supply_normal else "✗"
            operation = "✓" if record.operation_normal else "✗"
            cleaning = "✓" if record.cleaning_done else "✗"

            self.set_table_row(self.record_widget, row, [
                record.id,
                record.table.table_number if record.table else "",
                str(record.inspection_date),
                record.inspector or "-",
                status,
                tiles, dice, power, operation, cleaning
            ])

            status_item = self.record_widget.item(row, 4)
            if record.status == InspectionStatus.NORMAL:
                status_item.setForeground(QBrush(QColor("#4caf50")))
            elif record.status == InspectionStatus.ABNORMAL:
                status_item.setForeground(QBrush(QColor("#f44336")))
            elif record.status == InspectionStatus.REPAIRED:
                status_item.setForeground(QBrush(QColor("#ff9800")))
            else:
                status_item.setForeground(QBrush(QColor("#9e9e9e")))

            for col in range(5, 10):
                item = self.record_widget.item(row, col)
                if item and item.text() == "✓":
                    item.setForeground(QBrush(QColor("#4caf50")))
                elif item and item.text() == "✗":
                    item.setForeground(QBrush(QColor("#f44336")))
                if item:
                    item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        self.on_record_selected()

    def on_record_selected(self):
        self.detail_text.clear()
        record_id = self.get_selected_record_id()
        if record_id:
            record = self.inspection_service.get_inspection(record_id)
            if record:
                lines = []
                lines.append(f"桌号: {record.table.table_number if record.table else '-'}")
                lines.append(f"点检日期: {record.inspection_date}")
                lines.append(f"点检人: {record.inspector or '-'}")
                lines.append(f"状态: {record.status.value if record.status else '-'}")
                lines.append("")
                lines.append("点检项目:")
                lines.append(f"  麻将牌齐全: {'是' if record.tiles_complete else '否'}")
                lines.append(f"  骰子正常: {'是' if record.dice_normal else '否'}")
                lines.append(f"  电源正常: {'是' if record.power_supply_normal else '否'}")
                lines.append(f"  运行正常: {'是' if record.operation_normal else '否'}")
                lines.append(f"  已清洁: {'是' if record.cleaning_done else '否'}")
                lines.append("")
                if record.issues_found:
                    lines.append(f"发现问题: {record.issues_found}")
                if record.actions_taken:
                    lines.append(f"处理措施: {record.actions_taken}")
                if record.next_inspection_date:
                    lines.append(f"下次点检: {record.next_inspection_date}")
                if record.remark:
                    lines.append(f"备注: {record.remark}")
                self.detail_text.setPlainText("\n".join(lines))

    def get_selected_record_id(self):
        row = self.record_widget.currentRow()
        if row >= 0:
            return int(self.record_widget.item(row, 0).text())
        return None

    def batch_create(self):
        inspector, ok = QInputDialog.getText(self, "点检人", "请输入点检人姓名:")
        if ok:
            count = self.inspection_service.batch_create_weekly_inspections(inspector.strip() or None)
            self.show_info("成功", f"已创建 {count} 条点检记录")
            self.refresh()

    def add_inspection(self):
        tables = self.table_service.get_all_tables()
        if not tables:
            self.show_info("提示", "请先添加麻将桌")
            return
        dialog = InspectionDialog(self, tables)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.inspection_service.create_inspection(**data)
                self.show_info("成功", "点检记录创建成功")
                self.refresh()
            except Exception as e:
                self.show_error("错误", str(e))

    def edit_inspection(self):
        record_id = self.get_selected_record_id()
        if not record_id:
            self.show_info("提示", "请选择要修改的点检记录")
            return
        record = self.inspection_service.get_inspection(record_id)
        tables = self.table_service.get_all_tables()
        dialog = InspectionDialog(self, tables, record)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.inspection_service.update_inspection(record_id, **data)
                self.show_info("成功", "点检记录修改成功")
                self.refresh()
            except Exception as e:
                self.show_error("错误", str(e))

    def complete_inspection(self):
        record_id = self.get_selected_record_id()
        if not record_id:
            self.show_info("提示", "请选择要点检完成的记录")
            return
        record = self.inspection_service.get_inspection(record_id)
        if not record:
            return

        all_normal = all([
            record.tiles_complete, record.dice_normal,
            record.power_supply_normal, record.operation_normal, record.cleaning_done
        ])

        if self.show_confirm("确认", f"确认完成点检？检查结果为{'全部正常' if all_normal else '存在异常'}。"):
            updated = self.inspection_service.complete_inspection(record_id, is_normal=all_normal)
            if updated:
                self.show_info("成功", f"点检完成，状态: {updated.status.value}")
                self.refresh()
            else:
                self.show_error("错误", "操作失败")

    def mark_repaired(self):
        record_id = self.get_selected_record_id()
        if not record_id:
            self.show_info("提示", "请选择要标记维修的记录")
            return
        record = self.inspection_service.get_inspection(record_id)
        if record and record.status != InspectionStatus.ABNORMAL:
            self.show_info("提示", "只有异常状态的记录才能标记维修")
            return

        actions, ok = QInputDialog.getText(self, "维修处理", "请输入维修处理措施:")
        if ok:
            if self.inspection_service.mark_repaired(record_id, actions.strip() or None):
                self.show_info("成功", "已标记为已维修")
                self.refresh()
            else:
                self.show_error("错误", "操作失败")

    def delete_inspection(self):
        record_id = self.get_selected_record_id()
        if not record_id:
            self.show_info("提示", "请选择要删除的记录")
            return
        if self.show_confirm("确认", "确定要删除这条点检记录吗？"):
            if self.inspection_service.delete_inspection(record_id):
                self.show_info("成功", "记录删除成功")
                self.refresh()
            else:
                self.show_error("错误", "删除失败")
