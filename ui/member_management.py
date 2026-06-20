from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem,
                               QPushButton, QLabel, QGroupBox, QSplitter,
                               QComboBox, QDateEdit, QLineEdit, QCheckBox,
                               QTextEdit, QListWidget, QListWidgetItem,
                               QDoubleSpinBox, QSpinBox, QMessageBox,
                               QHeaderView, QFormLayout, QTabWidget)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush
from ui.base_widget import BaseWidget, BaseDialog
from modules.member_service import MemberService
from database.models import MemberLevel
from datetime import datetime


class MemberDialog(BaseDialog):
    def __init__(self, parent=None, member_data=None):
        self.member_data = member_data
        super().__init__("会员信息", parent)
        self.resize(450, 480)

    def init_dialog(self):
        self.edit_name = self.create_line_edit("请输入姓名")
        self.edit_phone = self.create_line_edit("请输入手机号")
        self.combo_level = self.create_combo([lv.value for lv in MemberLevel])
        self.spin_balance = self.create_double_spin(0, 100000, 2, " 元")
        self.edit_remark = self.create_text_edit("备注信息")

        self.add_field("姓名", self.edit_name, True)
        self.add_field("手机号", self.edit_phone, True)
        self.add_field("会员等级", self.combo_level)
        self.add_field("初始余额", self.spin_balance)
        self.add_field("备注", self.edit_remark)

        if self.member_data:
            self.edit_name.setText(self.member_data.name or "")
            self.edit_phone.setText(self.member_data.phone or "")
            idx = self.combo_level.findText(self.member_data.level.value)
            if idx >= 0:
                self.combo_level.setCurrentIndex(idx)
            self.spin_balance.setValue(self.member_data.balance or 0)
            self.edit_remark.setPlainText(self.member_data.remark or "")

    def get_data(self) -> dict:
        return {
            "name": self.edit_name.text().strip(),
            "phone": self.edit_phone.text().strip(),
            "level": MemberLevel(self.combo_level.currentText()),
            "balance": self.spin_balance.value(),
            "remark": self.edit_remark.toPlainText().strip() or None
        }

    def validate(self) -> bool:
        if not self.edit_name.text().strip():
            self.show_error("提示", "请输入姓名")
            return False
        if not self.edit_phone.text().strip():
            self.show_error("提示", "请输入手机号")
            return False
        return True


class RechargeDialog(BaseDialog):
    def __init__(self, parent=None, member_data=None):
        self.member_data = member_data
        super().__init__("会员充值", parent)
        self.resize(400, 300)

    def init_dialog(self):
        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; color: #1976d2;")
        self.spin_amount = self.create_double_spin(1, 100000, 2, " 元")
        self.spin_amount.setValue(100)
        self.edit_desc = self.create_line_edit("充值备注（可选）")

        self.add_field("会员信息", self.lbl_info)
        self.add_field("充值金额", self.spin_amount, True)
        self.add_field("备注", self.edit_desc)

        if self.member_data:
            self.lbl_info.setText(
                f"{self.member_data.name} ({self.member_data.phone}) | "
                f"当前余额: ¥{self.member_data.balance:.2f}"
            )

    def get_data(self) -> dict:
        return {
            "amount": self.spin_amount.value(),
            "description": self.edit_desc.text().strip() or None
        }

    def validate(self) -> bool:
        if self.spin_amount.value() <= 0:
            self.show_error("提示", "充值金额必须大于0")
            return False
        return True


class MemberManagementWidget(BaseWidget):
    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.member_service = MemberService(self.db)
        self.refresh()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("👤 会员档案")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1976d2;")
        main_layout.addWidget(title)

        splitter = QSplitter(Qt.Vertical)

        member_group = QGroupBox("会员列表")
        member_layout = QVBoxLayout(member_group)

        btn_layout = QHBoxLayout()
        self.btn_add = self.create_button("➕ 新增会员", callback=self.add_member)
        self.btn_edit = self.create_button("✏️ 修改", callback=self.edit_member)
        self.btn_recharge = self.create_button("💰 充值", callback=self.recharge_member)
        self.btn_disable = self.create_button("🚫 停用", callback=self.disable_member)
        self.btn_refresh = self.create_button("🔄 刷新", callback=self.refresh)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("姓名/手机号")
        self.edit_search.setMinimumHeight(32)
        self.edit_search.textChanged.connect(self.search_members)
        search_layout.addWidget(self.edit_search)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_recharge)
        btn_layout.addWidget(self.btn_disable)
        btn_layout.addStretch()
        btn_layout.addLayout(search_layout)
        btn_layout.addWidget(self.btn_refresh)
        member_layout.addLayout(btn_layout)

        self.member_table = self.create_table([
            "ID", "姓名", "手机号", "等级", "余额", "累计消费", "到店次数", "状态", "备注"
        ])
        member_layout.addWidget(self.member_table)

        splitter.addWidget(member_group)

        detail_group = QGroupBox("消费记录")
        detail_layout = QVBoxLayout(detail_group)
        self.consumption_table = self.create_table([
            "ID", "类型", "金额", "变动前余额", "变动后余额", "描述", "时间"
        ])
        detail_layout.addWidget(self.consumption_table)
        splitter.addWidget(detail_group)

        splitter.setSizes([400, 250])
        main_layout.addWidget(splitter)

        self.member_table.itemSelectionChanged.connect(self.on_member_selected)

    def refresh(self):
        self.refresh_members()

    def refresh_members(self):
        self.clear_table(self.member_table)
        members = self.member_service.get_all_members(only_active=False)
        for m in members:
            row = self.member_table.rowCount()
            self.member_table.insertRow(row)
            status = "正常" if m.is_active else "停用"
            self.set_table_row(self.member_table, row, [
                m.id, m.name, m.phone, m.level.value,
                f"¥{m.balance:.2f}", f"¥{m.total_consumption:.2f}",
                m.visit_count, status, m.remark or ""
            ])

            level_item = self.member_table.item(row, 3)
            if m.level == MemberLevel.DIAMOND:
                level_item.setForeground(QBrush(QColor("#9c27b0")))
            elif m.level == MemberLevel.GOLD:
                level_item.setForeground(QBrush(QColor("#ff9800")))
            elif m.level == MemberLevel.SILVER:
                level_item.setForeground(QBrush(QColor("#607d8b")))

            status_item = self.member_table.item(row, 7)
            if m.is_active:
                status_item.setForeground(QBrush(QColor("#4caf50")))
            else:
                status_item.setForeground(QBrush(QColor("#9e9e9e")))

    def search_members(self):
        keyword = self.edit_search.text().strip()
        self.clear_table(self.member_table)
        if keyword:
            members = self.member_service.get_member_by_name_or_phone(keyword)
        else:
            members = self.member_service.get_all_members(only_active=False)
        for m in members:
            row = self.member_table.rowCount()
            self.member_table.insertRow(row)
            status = "正常" if m.is_active else "停用"
            self.set_table_row(self.member_table, row, [
                m.id, m.name, m.phone, m.level.value,
                f"¥{m.balance:.2f}", f"¥{m.total_consumption:.2f}",
                m.visit_count, status, m.remark or ""
            ])

    def on_member_selected(self):
        member_id = self.get_selected_member_id()
        self.clear_table(self.consumption_table)
        if not member_id:
            return
        consumptions = self.member_service.get_consumptions(member_id)
        for c in consumptions:
            row = self.consumption_table.rowCount()
            self.consumption_table.insertRow(row)
            time_str = c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ""
            self.set_table_row(self.consumption_table, row, [
                c.id, c.type, f"¥{c.amount:.2f}",
                f"¥{c.balance_before:.2f}", f"¥{c.balance_after:.2f}",
                c.description or "", time_str
            ])
            type_item = self.consumption_table.item(row, 1)
            if c.type == "充值":
                type_item.setForeground(QBrush(QColor("#4caf50")))
            elif c.type == "消费":
                type_item.setForeground(QBrush(QColor("#f44336")))

    def get_selected_member_id(self):
        row = self.member_table.currentRow()
        if row >= 0:
            return int(self.member_table.item(row, 0).text())
        return None

    def add_member(self):
        dialog = MemberDialog(self)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.member_service.create_member(**data)
                self.show_info("成功", "会员创建成功")
                self.refresh_members()
            except Exception as e:
                self.show_error("错误", str(e))

    def edit_member(self):
        member_id = self.get_selected_member_id()
        if not member_id:
            self.show_info("提示", "请选择要修改的会员")
            return
        member = self.member_service.get_member(member_id)
        if not member:
            self.show_error("错误", "会员不存在")
            return
        dialog = MemberDialog(self, member)
        if dialog.exec():
            try:
                data = dialog.get_data()
                data.pop("balance", None)
                self.member_service.update_member(member_id, **data)
                self.show_info("成功", "会员修改成功")
                self.refresh_members()
            except Exception as e:
                self.show_error("错误", str(e))

    def recharge_member(self):
        member_id = self.get_selected_member_id()
        if not member_id:
            self.show_info("提示", "请选择要充值的会员")
            return
        member = self.member_service.get_member(member_id)
        if not member:
            self.show_error("错误", "会员不存在")
            return
        dialog = RechargeDialog(self, member)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.member_service.recharge(member_id, data["amount"], data["description"] or "")
                self.show_info("成功", f"充值成功！余额: ¥{member.balance + data['amount']:.2f}")
                self.refresh()
            except Exception as e:
                self.show_error("错误", str(e))

    def disable_member(self):
        member_id = self.get_selected_member_id()
        if not member_id:
            self.show_info("提示", "请选择要停用的会员")
            return
        if self.show_confirm("确认", "确定要停用该会员吗？"):
            if self.member_service.delete_member(member_id):
                self.show_info("成功", "会员已停用")
                self.refresh()
            else:
                self.show_error("错误", "停用失败")
