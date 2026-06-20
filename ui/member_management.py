from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem,
                               QPushButton, QLabel, QGroupBox, QSplitter,
                               QComboBox, QDateEdit, QLineEdit, QCheckBox,
                               QTextEdit, QListWidget, QListWidgetItem,
                               QDoubleSpinBox, QSpinBox, QMessageBox,
                               QHeaderView, QFormLayout, QTabWidget, QDialog,
                               QRadioButton, QButtonGroup)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush
from ui.base_widget import BaseWidget, BaseDialog
from modules.member_service import MemberService
from database.models import MemberLevel
from datetime import datetime, date


class MemberDialog(BaseDialog):
    def __init__(self, parent=None, member_data=None, member_service=None):
        self.member_data = member_data
        self.member_service = member_service
        super().__init__("会员信息", parent)
        self.resize(480, 520)

    def init_dialog(self):
        self.edit_name = self.create_line_edit("请输入姓名")
        self.edit_phone = self.create_line_edit("请输入手机号")
        self.combo_level = self.create_combo([lv.value for lv in MemberLevel])
        self.combo_level.currentTextChanged.connect(self._update_level_info)
        self.spin_balance = self.create_double_spin(0, 100000, 2, " 元")
        self.edit_remark = self.create_text_edit("备注信息")

        self.lbl_level_discount = QLabel("")
        self.lbl_level_discount.setStyleSheet("color: #f44336; font-weight: bold;")

        self.add_field("姓名", self.edit_name, True)
        self.add_field("手机号", self.edit_phone, True)
        self.add_field("会员等级", self.combo_level)
        self.add_field("等级折扣", self.lbl_level_discount)
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
        else:
            self._update_level_info()

    def _update_level_info(self):
        if self.member_service:
            level_name = self.combo_level.currentText()
            try:
                level = MemberLevel(level_name)
                discount = self.member_service.get_level_discount(level)
                if discount < 10:
                    self.lbl_level_discount.setText(f"{discount}折优惠")
                else:
                    self.lbl_level_discount.setText("无折扣")
            except:
                self.lbl_level_discount.setText("")

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
    def __init__(self, parent=None, member_data=None, member_service=None):
        self.member_data = member_data
        self.member_service = member_service
        super().__init__("会员充值", parent)
        self.resize(480, 420)

    def init_dialog(self):
        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; color: #1976d2;")

        self.radio_custom = QRadioButton("自定义金额")
        self.radio_package = QRadioButton("储值套餐")
        self.radio_custom.setChecked(True)
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.radio_custom, 0)
        self.btn_group.addButton(self.radio_package, 1)
        self.radio_custom.toggled.connect(self._on_mode_changed)

        self.spin_amount = self.create_double_spin(1, 100000, 2, " 元")
        self.spin_amount.setValue(100)

        self.combo_package = self.create_combo([])
        self.combo_package.setEnabled(False)
        self.lbl_package_bonus = QLabel("")
        self.lbl_package_bonus.setStyleSheet("color: #4caf50; font-weight: bold;")

        self.edit_desc = self.create_line_edit("充值备注（可选）")

        self.add_field("会员信息", self.lbl_info)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self.radio_custom)
        mode_layout.addWidget(self.radio_package)
        mode_widget = QWidget()
        mode_widget.setLayout(mode_layout)
        self.add_field("充值方式", mode_widget)

        self.add_field("充值金额", self.spin_amount)

        package_layout = QVBoxLayout()
        package_layout.addWidget(self.combo_package)
        package_layout.addWidget(self.lbl_package_bonus)
        package_widget = QWidget()
        package_widget.setLayout(package_layout)
        self.add_field("储值套餐", package_widget)

        self.add_field("备注", self.edit_desc)

        if self.member_data:
            self.lbl_info.setText(
                f"{self.member_data.name} ({self.member_data.phone}) | "
                f"当前余额: ¥{self.member_data.balance:.2f}"
            )

        self._load_packages()

    def _load_packages(self):
        if not self.member_service:
            return
        packages = self.member_service.get_recharge_packages(only_active=True)
        for pkg in packages:
            desc = f"{pkg.name} - 充¥{pkg.recharge_amount:.0f}送¥{pkg.bonus_amount:.0f}"
            self.combo_package.addItem(desc, pkg.id)
        if packages:
            self._on_package_changed(0)
            self.combo_package.currentIndexChanged.connect(self._on_package_changed)

    def _on_package_changed(self, idx):
        if idx < 0 or not self.member_service:
            return
        pkg_id = self.combo_package.itemData(idx)
        if not pkg_id:
            return
        pkg = self.member_service.get_recharge_package(pkg_id)
        if pkg:
            self.lbl_package_bonus.setText(
                f"赠送: ¥{pkg.bonus_amount:.0f} | 到账: ¥{pkg.recharge_amount + pkg.bonus_amount:.0f}"
            )

    def _on_mode_changed(self, checked):
        is_custom = self.radio_custom.isChecked()
        self.spin_amount.setEnabled(is_custom)
        self.combo_package.setEnabled(not is_custom)
        self.lbl_package_bonus.setEnabled(not is_custom)

    def get_data(self) -> dict:
        use_package = self.radio_package.isChecked()
        if use_package:
            idx = self.combo_package.currentIndex()
            package_id = self.combo_package.itemData(idx) if idx >= 0 else None
            return {
                "use_package": True,
                "package_id": package_id,
                "description": self.edit_desc.text().strip() or None
            }
        else:
            return {
                "use_package": False,
                "amount": self.spin_amount.value(),
                "description": self.edit_desc.text().strip() or None
            }

    def validate(self) -> bool:
        data = self.get_data()
        if data["use_package"]:
            if not data.get("package_id"):
                self.show_error("提示", "请选择储值套餐")
                return False
        else:
            if data["amount"] <= 0:
                self.show_error("提示", "充值金额必须大于0")
                return False
        return True


class ConsumptionDetailDialog(BaseDialog):
    def __init__(self, parent=None, consumption=None, bill=None):
        self.consumption = consumption
        self.bill = bill
        super().__init__("消费详情", parent)
        self.resize(500, 520)

    def init_dialog(self):
        c = self.consumption
        if not c:
            return

        self.lbl_type = QLabel(c.type or "")
        self.lbl_type.setStyleSheet("font-size: 16px; font-weight: bold; color: #1976d2;")
        self.add_field("交易类型", self.lbl_type)

        self.lbl_amount = QLabel(f"¥{c.amount:.2f}")
        self.lbl_amount.setStyleSheet("font-size: 18px; font-weight: bold; color: #f44336;")
        self.add_field("交易金额", self.lbl_amount)

        time_str = c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else ""
        self.add_field("交易时间", QLabel(time_str))

        self.add_field("变动前余额", QLabel(f"¥{c.balance_before:.2f}"))
        self.add_field("变动后余额", QLabel(f"¥{c.balance_after:.2f}"))

        if hasattr(c, 'bill_no') and c.bill_no:
            self.add_field("账单号", QLabel(c.bill_no))
        if hasattr(c, 'table_number') and c.table_number:
            self.add_field("桌号", QLabel(c.table_number))

        if hasattr(c, 'member_discount') and c.member_discount is not None and c.member_discount > 0:
            self.add_field("会员折扣", QLabel(f"-¥{c.member_discount:.2f}"))
        if hasattr(c, 'coupon_discount') and c.coupon_discount is not None and c.coupon_discount > 0:
            self.add_field("优惠券折扣", QLabel(f"-¥{c.coupon_discount:.2f}"))
        if hasattr(c, 'recharge_amount') and c.recharge_amount is not None and c.recharge_amount > 0:
            self.add_field("本金", QLabel(f"¥{c.recharge_amount:.2f}"))
        if hasattr(c, 'bonus_amount') and c.bonus_amount is not None and c.bonus_amount > 0:
            self.add_field("赠送金", QLabel(f"¥{c.bonus_amount:.2f}"))

        self.add_field("描述", QLabel(c.description or ""))

        if hasattr(c, 'discount_detail') and c.discount_detail:
            detail_group = QGroupBox("优惠明细")
            detail_layout = QVBoxLayout(detail_group)
            detail_text = QTextEdit()
            detail_text.setReadOnly(True)
            detail_text.setPlainText(c.discount_detail)
            detail_text.setStyleSheet("font-family: Consolas, Monaco, monospace; font-size: 12px;")
            detail_text.setMaximumHeight(120)
            detail_layout.addWidget(detail_text)
            self.form_layout.addRow(detail_group)

    def get_data(self) -> dict:
        return {}

    def validate(self) -> bool:
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

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_member_tab(), "📋 会员管理")
        self.tabs.addTab(self._create_benefit_tab(), "🎁 等级权益")
        main_layout.addWidget(self.tabs)

    def _create_member_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)

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
            "ID", "姓名", "手机号", "等级", "折扣", "余额", "累计消费", "累计优惠", "到店次数", "状态", "备注"
        ])
        member_layout.addWidget(self.member_table)

        splitter.addWidget(member_group)

        detail_group = QGroupBox("消费记录（双击查看详情）")
        detail_layout = QVBoxLayout(detail_group)

        detail_btn_layout = QHBoxLayout()
        self.btn_view_detail = self.create_button("📋 查看详情", callback=self.view_consumption_detail)
        detail_btn_layout.addWidget(self.btn_view_detail)
        detail_btn_layout.addStretch()
        detail_layout.addLayout(detail_btn_layout)

        self.consumption_table = self.create_table([
            "ID", "类型", "金额", "账单号", "桌号", "会员折扣", "优惠券折扣", "余额", "时间"
        ])
        detail_layout.addWidget(self.consumption_table)
        splitter.addWidget(detail_group)

        splitter.setSizes([350, 300])
        layout.addWidget(splitter)

        self.member_table.itemSelectionChanged.connect(self.on_member_selected)
        self.consumption_table.itemDoubleClicked.connect(lambda: self.view_consumption_detail())

        return tab

    def _create_benefit_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        level_group = QGroupBox("会员等级权益")
        level_layout = QVBoxLayout(level_group)

        levels_info = [
            ("普通会员", "10折", "无", "注册即享"),
            ("银卡会员", "9.5折", "95折优惠", "消费满1000元升级"),
            ("金卡会员", "9折", "9折优惠", "消费满3000元升级"),
            ("钻石会员", "8.5折", "85折优惠", "消费满10000元升级"),
        ]

        level_table = self.create_table(["等级", "折扣率", "权益", "升级条件"])
        for level, discount, benefit, condition in levels_info:
            row = level_table.rowCount()
            level_table.insertRow(row)
            self.set_table_row(level_table, row, [level, discount, benefit, condition])
            level_item = level_table.item(row, 0)
            if level == "钻石会员":
                level_item.setForeground(QBrush(QColor("#9c27b0")))
                level_item.setFont(level_item.font())
            elif level == "金卡会员":
                level_item.setForeground(QBrush(QColor("#ff9800")))
            elif level == "银卡会员":
                level_item.setForeground(QBrush(QColor("#607d8b")))

        level_layout.addWidget(level_table)
        layout.addWidget(level_group)

        package_group = QGroupBox("储值套餐")
        package_layout = QVBoxLayout(package_group)

        pkg_btn_layout = QHBoxLayout()
        self.btn_add_package = self.create_button("➕ 新增套餐", callback=self.add_package)
        self.btn_edit_package = self.create_button("✏️ 修改", callback=self.edit_package)
        self.btn_del_package = self.create_button("🗑️ 删除", callback=self.delete_package)
        self.btn_refresh_pkg = self.create_button("🔄 刷新", callback=self.refresh_packages)
        pkg_btn_layout.addWidget(self.btn_add_package)
        pkg_btn_layout.addWidget(self.btn_edit_package)
        pkg_btn_layout.addWidget(self.btn_del_package)
        pkg_btn_layout.addStretch()
        pkg_btn_layout.addWidget(self.btn_refresh_pkg)
        package_layout.addLayout(pkg_btn_layout)

        self.package_table = self.create_table([
            "ID", "套餐名称", "充值金额", "赠送金额", "总到账", "排序", "状态"
        ])
        package_layout.addWidget(self.package_table)

        layout.addWidget(package_group)

        return tab

    def refresh(self):
        self.refresh_members()
        self.refresh_packages()

    def refresh_members(self):
        self.clear_table(self.member_table)
        members = self.member_service.get_all_members(only_active=False)
        for m in members:
            row = self.member_table.rowCount()
            self.member_table.insertRow(row)
            status = "正常" if m.is_active else "停用"
            discount = self.member_service.get_level_discount(m.level)
            discount_str = f"{discount}折" if discount < 10 else "无"
            total_saved = 0.0
            if hasattr(m, 'total_saved') and m.total_saved:
                total_saved = m.total_saved
            self.set_table_row(self.member_table, row, [
                m.id, m.name, m.phone, m.level.value, discount_str,
                f"¥{m.balance:.2f}", f"¥{m.total_consumption:.2f}",
                f"¥{total_saved:.2f}", m.visit_count, status, m.remark or ""
            ])

            level_item = self.member_table.item(row, 3)
            if m.level == MemberLevel.DIAMOND:
                level_item.setForeground(QBrush(QColor("#9c27b0")))
            elif m.level == MemberLevel.GOLD:
                level_item.setForeground(QBrush(QColor("#ff9800")))
            elif m.level == MemberLevel.SILVER:
                level_item.setForeground(QBrush(QColor("#607d8b")))

            status_item = self.member_table.item(row, 9)
            if m.is_active:
                status_item.setForeground(QBrush(QColor("#4caf50")))
            else:
                status_item.setForeground(QBrush(QColor("#9e9e9e")))

    def refresh_packages(self):
        if not hasattr(self, 'package_table'):
            return
        self.clear_table(self.package_table)
        packages = self.member_service.get_recharge_packages(only_active=False)
        for pkg in packages:
            row = self.package_table.rowCount()
            self.package_table.insertRow(row)
            status = "启用" if pkg.is_active else "停用"
            total = pkg.recharge_amount + pkg.bonus_amount
            self.set_table_row(self.package_table, row, [
                pkg.id, pkg.name, f"¥{pkg.recharge_amount:.0f}",
                f"¥{pkg.bonus_amount:.0f}", f"¥{total:.0f}",
                pkg.sort_order, status
            ])
            status_item = self.package_table.item(row, 6)
            if pkg.is_active:
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
            discount = self.member_service.get_level_discount(m.level)
            discount_str = f"{discount}折" if discount < 10 else "无"
            total_saved = 0.0
            if hasattr(m, 'total_saved') and m.total_saved:
                total_saved = m.total_saved
            self.set_table_row(self.member_table, row, [
                m.id, m.name, m.phone, m.level.value, discount_str,
                f"¥{m.balance:.2f}", f"¥{m.total_consumption:.2f}",
                f"¥{total_saved:.2f}", m.visit_count, status, m.remark or ""
            ])

    def on_member_selected(self):
        member_id = self.get_selected_member_id()
        self.clear_table(self.consumption_table)
        if not member_id:
            return
        consumptions = self.member_service.get_consumptions(member_id, limit=100)
        for c in consumptions:
            row = self.consumption_table.rowCount()
            self.consumption_table.insertRow(row)
            time_str = c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ""

            bill_no = c.bill_no if hasattr(c, 'bill_no') and c.bill_no else "-"
            table_number = c.table_number if hasattr(c, 'table_number') and c.table_number else "-"
            m_disc = f"-¥{c.member_discount:.2f}" if hasattr(c, 'member_discount') and c.member_discount and c.member_discount > 0 else "-"
            c_disc = f"-¥{c.coupon_discount:.2f}" if hasattr(c, 'coupon_discount') and c.coupon_discount and c.coupon_discount > 0 else "-"

            self.set_table_row(self.consumption_table, row, [
                c.id, c.type, f"¥{c.amount:.2f}",
                bill_no, table_number, m_disc, c_disc,
                f"¥{c.balance_after:.2f}", time_str
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

    def get_selected_consumption_id(self):
        row = self.consumption_table.currentRow()
        if row >= 0:
            return int(self.consumption_table.item(row, 0).text())
        return None

    def add_member(self):
        dialog = MemberDialog(self, member_service=self.member_service)
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
        dialog = MemberDialog(self, member, self.member_service)
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
        dialog = RechargeDialog(self, member, self.member_service)
        if dialog.exec():
            try:
                data = dialog.get_data()
                desc = data["description"] or ""
                if data["use_package"]:
                    self.member_service.recharge_with_package(member_id, data["package_id"])
                else:
                    self.member_service.recharge(member_id, data["amount"], desc)
                member = self.member_service.get_member(member_id)
                self.show_info("成功", f"充值成功！当前余额: ¥{member.balance:.2f}")
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

    def view_consumption_detail(self):
        member_id = self.get_selected_member_id()
        if not member_id:
            self.show_info("提示", "请先选择会员")
            return
        consumption_id = self.get_selected_consumption_id()
        if not consumption_id:
            self.show_info("提示", "请选择要查看的消费记录")
            return

        consumptions = self.member_service.get_consumptions(member_id, limit=200)
        target = None
        for c in consumptions:
            if c.id == consumption_id:
                target = c
                break
        if not target:
            self.show_error("错误", "消费记录不存在")
            return

        dialog = ConsumptionDetailDialog(self, target)
        dialog.exec()

    def add_package(self):
        from ui.base_widget import BaseDialog
        dialog = BaseDialog("新增储值套餐", self)
        dialog.resize(400, 350)

        def _init():
            nonlocal dialog
            dialog.edit_name = dialog.create_line_edit("套餐名称，如: 充500送50")
            dialog.spin_recharge = dialog.create_double_spin(0, 100000, 2, " 元")
            dialog.spin_bonus = dialog.create_double_spin(0, 100000, 2, " 元")
            dialog.spin_sort = dialog.create_spin(0, 1000, 1)
            dialog.chk_active = QCheckBox("启用")
            dialog.chk_active.setChecked(True)
            dialog.edit_desc = dialog.create_text_edit("套餐描述（可选）")

            dialog.add_field("套餐名称", dialog.edit_name, True)
            dialog.add_field("充值金额", dialog.spin_recharge, True)
            dialog.add_field("赠送金额", dialog.spin_bonus)
            dialog.add_field("排序权重", dialog.spin_sort)
            dialog.add_field("状态", dialog.chk_active)
            dialog.add_field("描述", dialog.edit_desc)

        dialog.init_dialog = _init
        _init()

        def _validate():
            if not dialog.edit_name.text().strip():
                dialog.show_error("提示", "请输入套餐名称")
                return False
            if dialog.spin_recharge.value() <= 0:
                dialog.show_error("提示", "充值金额必须大于0")
                return False
            return True

        dialog.validate = _validate

        if dialog.exec():
            try:
                self.member_service.create_recharge_package(
                    name=dialog.edit_name.text().strip(),
                    recharge_amount=dialog.spin_recharge.value(),
                    bonus_amount=dialog.spin_bonus.value(),
                    sort_order=dialog.spin_sort.value(),
                    is_active=dialog.chk_active.isChecked(),
                    description=dialog.edit_desc.toPlainText().strip() or None
                )
                self.show_info("成功", "套餐创建成功")
                self.refresh_packages()
            except Exception as e:
                self.show_error("错误", str(e))

    def edit_package(self):
        row = self.package_table.currentRow()
        if row < 0:
            self.show_info("提示", "请选择要修改的套餐")
            return
        pkg_id = int(self.package_table.item(row, 0).text())
        pkg = self.member_service.get_recharge_package(pkg_id)
        if not pkg:
            self.show_error("错误", "套餐不存在")
            return

        from ui.base_widget import BaseDialog
        dialog = BaseDialog("修改储值套餐", self)
        dialog.resize(400, 350)

        def _init():
            nonlocal dialog
            dialog.edit_name = dialog.create_line_edit("套餐名称")
            dialog.spin_recharge = dialog.create_double_spin(0, 100000, 2, " 元")
            dialog.spin_bonus = dialog.create_double_spin(0, 100000, 2, " 元")
            dialog.spin_sort = dialog.create_spin(0, 1000, 1)
            dialog.chk_active = QCheckBox("启用")
            dialog.edit_desc = dialog.create_text_edit("套餐描述（可选）")

            dialog.add_field("套餐名称", dialog.edit_name, True)
            dialog.add_field("充值金额", dialog.spin_recharge, True)
            dialog.add_field("赠送金额", dialog.spin_bonus)
            dialog.add_field("排序权重", dialog.spin_sort)
            dialog.add_field("状态", dialog.chk_active)
            dialog.add_field("描述", dialog.edit_desc)

            dialog.edit_name.setText(pkg.name or "")
            dialog.spin_recharge.setValue(pkg.recharge_amount or 0)
            dialog.spin_bonus.setValue(pkg.bonus_amount or 0)
            dialog.spin_sort.setValue(pkg.sort_order or 0)
            dialog.chk_active.setChecked(pkg.is_active if pkg.is_active is not None else True)
            dialog.edit_desc.setPlainText(pkg.description or "")

        dialog.init_dialog = _init
        _init()

        def _validate():
            if not dialog.edit_name.text().strip():
                dialog.show_error("提示", "请输入套餐名称")
                return False
            if dialog.spin_recharge.value() <= 0:
                dialog.show_error("提示", "充值金额必须大于0")
                return False
            return True

        dialog.validate = _validate

        if dialog.exec():
            try:
                self.member_service.update_recharge_package(
                    pkg_id,
                    name=dialog.edit_name.text().strip(),
                    recharge_amount=dialog.spin_recharge.value(),
                    bonus_amount=dialog.spin_bonus.value(),
                    sort_order=dialog.spin_sort.value(),
                    is_active=dialog.chk_active.isChecked(),
                    description=dialog.edit_desc.toPlainText().strip() or None
                )
                self.show_info("成功", "套餐修改成功")
                self.refresh_packages()
            except Exception as e:
                self.show_error("错误", str(e))

    def delete_package(self):
        row = self.package_table.currentRow()
        if row < 0:
            self.show_info("提示", "请选择要删除的套餐")
            return
        if self.show_confirm("确认", "确定要停用该套餐吗？"):
            pkg_id = int(self.package_table.item(row, 0).text())
            if self.member_service.delete_recharge_package(pkg_id):
                self.show_info("成功", "套餐已停用")
                self.refresh_packages()
            else:
                self.show_error("错误", "操作失败")
