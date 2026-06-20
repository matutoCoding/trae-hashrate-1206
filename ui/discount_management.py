from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem,
                               QPushButton, QLabel, QGroupBox, QSplitter,
                               QComboBox, QDateEdit, QLineEdit, QCheckBox,
                               QTextEdit, QListWidget, QListWidgetItem,
                               QDoubleSpinBox, QSpinBox)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush
from ui.base_widget import BaseWidget, BaseDialog
from modules.discount_service import DiscountService
from database.models import CouponType, DiscountApplyOrder
from datetime import date


class CouponDialog(BaseDialog):
    def __init__(self, parent=None, coupon_data=None):
        self.coupon_data = coupon_data
        super().__init__("优惠券信息", parent)
        self.resize(500, 600)

    def init_dialog(self):
        self.edit_code = self.create_line_edit("如：DISCOUNT001")
        self.edit_name = self.create_line_edit("如：新客8折券")
        self.combo_type = self.create_combo([t.value for t in CouponType])
        self.spin_discount = self.create_double_spin(0, 1000, 2)
        self.spin_min = self.create_double_spin(0, 10000, 2, " 元")
        self.spin_max = self.create_double_spin(0, 10000, 2, " 元")
        self.chk_has_max = QCheckBox("设置最高优惠")
        self.chk_has_max.toggled.connect(self.spin_max.setEnabled)
        self.spin_max.setEnabled(False)
        self.date_from = self.create_date_edit()
        self.date_to = self.create_date_edit()
        self.date_to.setDate(QDate.currentDate().addMonths(1))
        self.chk_has_from = QCheckBox("设置有效期开始")
        self.chk_has_from.setChecked(False)
        self.chk_has_from.toggled.connect(self.date_from.setEnabled)
        self.date_from.setEnabled(False)
        self.chk_has_to = QCheckBox("设置有效期结束")
        self.chk_has_to.setChecked(True)
        self.chk_has_to.toggled.connect(self.date_to.setEnabled)
        self.spin_quantity = self.create_spin(1, 10000, " 张")
        self.chk_active = QCheckBox("启用")
        self.chk_active.setChecked(True)
        self.edit_description = self.create_text_edit("备注信息")

        self.add_field("券号", self.edit_code, True)
        self.add_field("名称", self.edit_name, True)
        self.add_field("类型", self.combo_type, True)
        self.add_field("面值", self.spin_discount, True)
        self.lbl_type_hint = QLabel("折扣券：输入折扣率（如8表示8折），满减券：输入减免金额")
        self.lbl_type_hint.setStyleSheet("color: #666; font-size: 11px;")
        self.form_layout.addRow("", self.lbl_type_hint)

        self.add_field("最低消费", self.spin_min)

        max_layout = QHBoxLayout()
        max_layout.addWidget(self.chk_has_max)
        max_layout.addWidget(self.spin_max)
        self.add_field("最高优惠", max_layout)

        from_layout = QHBoxLayout()
        from_layout.addWidget(self.chk_has_from)
        from_layout.addWidget(self.date_from)
        self.add_field("有效期开始", from_layout)

        to_layout = QHBoxLayout()
        to_layout.addWidget(self.chk_has_to)
        to_layout.addWidget(self.date_to)
        self.add_field("有效期结束", to_layout)

        self.add_field("发行数量", self.spin_quantity)
        self.add_field("状态", self.chk_active)
        self.add_field("备注", self.edit_description)

        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        self._on_type_changed()

        if self.coupon_data:
            self.edit_code.setText(self.coupon_data.code)
            self.edit_name.setText(self.coupon_data.name)
            idx = self.combo_type.findText(self.coupon_data.type.value)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)
            self.spin_discount.setValue(self.coupon_data.discount_value)
            self.spin_min.setValue(self.coupon_data.min_consumption)
            if self.coupon_data.max_discount:
                self.chk_has_max.setChecked(True)
                self.spin_max.setValue(self.coupon_data.max_discount)
            if self.coupon_data.valid_from:
                self.chk_has_from.setChecked(True)
                self.date_from.setDate(QDate(self.coupon_data.valid_from.year,
                                            self.coupon_data.valid_from.month,
                                            self.coupon_data.valid_from.day))
            if self.coupon_data.valid_to:
                self.chk_has_to.setChecked(True)
                self.date_to.setDate(QDate(self.coupon_data.valid_to.year,
                                          self.coupon_data.valid_to.month,
                                          self.coupon_data.valid_to.day))
            self.spin_quantity.setValue(self.coupon_data.total_quantity)
            self.chk_active.setChecked(self.coupon_data.is_active)
            self.edit_description.setPlainText(self.coupon_data.description or "")

    def _on_type_changed(self):
        ctype = self.combo_type.currentText()
        if ctype == CouponType.DISCOUNT.value:
            self.spin_discount.setSuffix(" 折")
            self.spin_discount.setRange(0.1, 10)
            self.lbl_type_hint.setText("折扣券：输入折扣率（如8表示8折，7.5表示75折）")
        else:
            self.spin_discount.setSuffix(" 元")
            self.spin_discount.setRange(0, 10000)
            self.lbl_type_hint.setText("满减券：输入减免金额")

    def get_data(self) -> dict:
        return {
            "code": self.edit_code.text().strip(),
            "name": self.edit_name.text().strip(),
            "coupon_type": CouponType(self.combo_type.currentText()),
            "discount_value": self.spin_discount.value(),
            "min_consumption": self.spin_min.value(),
            "max_discount": self.spin_max.value() if self.chk_has_max.isChecked() else None,
            "valid_from": self.date_from.date().toPython() if self.chk_has_from.isChecked() else None,
            "valid_to": self.date_to.date().toPython() if self.chk_has_to.isChecked() else None,
            "total_quantity": self.spin_quantity.value(),
            "is_active": self.chk_active.isChecked(),
            "description": self.edit_description.toPlainText().strip() or None
        }

    def validate(self) -> bool:
        if not self.edit_code.text().strip():
            self.show_error("提示", "请输入券号")
            return False
        if not self.edit_name.text().strip():
            self.show_error("提示", "请输入名称")
            return False
        if self.spin_discount.value() <= 0:
            self.show_error("提示", "面值必须大于0")
            return False
        return True


class DiscountConfigDialog(BaseDialog):
    def __init__(self, parent=None, config_data=None):
        self.config_data = config_data
        super().__init__("优惠计算配置", parent)
        self.resize(450, 250)

    def init_dialog(self):
        self.combo_order = self.create_combo([o.value for o in DiscountApplyOrder])
        self.chk_allow_negative = QCheckBox("允许优惠后金额为负")
        self.chk_allow_negative.setChecked(False)

        self.add_field("优惠计算顺序", self.combo_order, True)
        self.add_field("负值设置", self.chk_allow_negative)

        hint = QLabel("⚠️ 负值兜底校验：如果不允许负值，优惠后金额小于0时将自动调整为0")
        hint.setStyleSheet("color: #f44336; font-size: 11px;")
        self.form_layout.addRow("", hint)

        if self.config_data:
            idx = self.combo_order.findText(self.config_data.apply_order.value)
            if idx >= 0:
                self.combo_order.setCurrentIndex(idx)
            self.chk_allow_negative.setChecked(self.config_data.allow_negative)

    def get_data(self) -> dict:
        return {
            "apply_order": DiscountApplyOrder(self.combo_order.currentText()),
            "allow_negative": self.chk_allow_negative.isChecked()
        }


class DiscountManagementWidget(BaseWidget):
    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.discount_service = DiscountService(self.db)
        self.selected_coupons = []
        self.refresh()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("💰 优惠计算管理")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1976d2;")
        main_layout.addWidget(title)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        coupon_group = QGroupBox("优惠券列表")
        coupon_layout = QVBoxLayout(coupon_group)

        btn_layout = QHBoxLayout()
        self.btn_add = self.create_button("➕ 添加", callback=self.add_coupon)
        self.btn_edit = self.create_button("✏️ 修改", callback=self.edit_coupon)
        self.btn_delete = self.create_button("🗑️ 删除", callback=self.delete_coupon)
        self.btn_config = self.create_button("⚙️ 计算配置", callback=self.edit_config)
        self.btn_refresh = self.create_button("🔄 刷新", callback=self.refresh)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_config)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_refresh)
        coupon_layout.addLayout(btn_layout)

        self.coupon_widget = self.create_table([
            "ID", "券号", "名称", "类型", "面值", "最低消费", "已用/总数", "有效期", "状态"
        ])
        coupon_layout.addWidget(self.coupon_widget)

        left_layout.addWidget(coupon_group)

        config_group = QGroupBox("当前优惠配置")
        config_layout = QVBoxLayout(config_group)
        self.lbl_config = QLabel("加载中...")
        self.lbl_config.setStyleSheet("font-size: 13px; padding: 8px; background: #f5f5f5; border-radius: 4px;")
        config_layout.addWidget(self.lbl_config)
        left_layout.addWidget(config_group)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        calc_group = QGroupBox("优惠计算器")
        calc_layout = QVBoxLayout(calc_group)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("原始金额:"))
        self.spin_amount = self.create_double_spin(0, 100000, 2, " 元")
        self.spin_amount.setValue(200)
        self.spin_amount.valueChanged.connect(self.calculate)
        input_layout.addWidget(self.spin_amount)
        input_layout.addStretch()
        calc_layout.addLayout(input_layout)

        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("选择优惠券:"))
        self.btn_add_selected = self.create_button("→ 添加", callback=self.add_selected_coupon)
        self.btn_remove_selected = self.create_button("← 移除", callback=self.remove_selected_coupon)
        self.btn_clear_selected = self.create_button("清空", callback=self.clear_selected_coupons)
        select_layout.addWidget(self.btn_add_selected)
        select_layout.addWidget(self.btn_remove_selected)
        select_layout.addWidget(self.btn_clear_selected)
        select_layout.addStretch()
        calc_layout.addLayout(select_layout)

        list_splitter = QSplitter(Qt.Horizontal)

        available_group = QGroupBox("可用优惠券")
        available_layout = QVBoxLayout(available_group)
        self.list_available = QListWidget()
        self.list_available.setSelectionMode(QListWidget.MultiSelection)
        available_layout.addWidget(self.list_available)
        list_splitter.addWidget(available_group)

        selected_group = QGroupBox("已选优惠券")
        selected_layout = QVBoxLayout(selected_group)
        self.list_selected = QListWidget()
        self.list_selected.setSelectionMode(QListWidget.MultiSelection)
        selected_layout.addWidget(self.list_selected)
        list_splitter.addWidget(selected_group)

        calc_layout.addWidget(list_splitter)
        self.btn_calc = self.create_button("🧮 计算优惠", callback=self.calculate)
        calc_layout.addWidget(self.btn_calc)

        result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("font-family: Consolas, Monaco, monospace; font-size: 12px;")
        result_layout.addWidget(self.result_text)
        calc_layout.addWidget(result_group)

        right_layout.addWidget(calc_group)
        splitter.addWidget(right_widget)

        splitter.setSizes([600, 500])
        main_layout.addWidget(splitter)

    def refresh(self):
        self.refresh_coupons()
        self.refresh_config()
        self.refresh_available_coupons()

    def refresh_coupons(self):
        self.clear_table(self.coupon_widget)
        coupons = self.discount_service.get_all_coupons(only_active=False)
        for coupon in coupons:
            row = self.coupon_widget.rowCount()
            self.coupon_widget.insertRow(row)

            if coupon.type == CouponType.DISCOUNT:
                face_value = f"{coupon.discount_value}折"
            else:
                face_value = f"¥{coupon.discount_value}"

            valid_str = ""
            if coupon.valid_from and coupon.valid_to:
                valid_str = f"{coupon.valid_from} ~ {coupon.valid_to}"
            elif coupon.valid_from:
                valid_str = f"自{coupon.valid_from}"
            elif coupon.valid_to:
                valid_str = f"至{coupon.valid_to}"

            status = "启用" if coupon.is_active else "停用"
            quantity = f"{coupon.used_quantity}/{coupon.total_quantity}"

            self.set_table_row(self.coupon_widget, row, [
                coupon.id, coupon.code, coupon.name, coupon.type.value,
                face_value, f"¥{coupon.min_consumption}", quantity, valid_str, status
            ])

            type_item = self.coupon_widget.item(row, 3)
            if coupon.type == CouponType.DISCOUNT:
                type_item.setForeground(QBrush(QColor("#2196f3")))
            else:
                type_item.setForeground(QBrush(QColor("#ff9800")))

            status_item = self.coupon_widget.item(row, 8)
            status_item.setForeground(QBrush(QColor("#4caf50" if coupon.is_active else "#9e9e9e")))

    def refresh_config(self):
        config = self.discount_service.get_discount_config()
        if config:
            order_text = config.apply_order.value
            negative_text = "允许负值" if config.allow_negative else "禁止负值（自动兜底为0）"
            self.lbl_config.setText(f"📌 当前配置：{order_text} | {negative_text}")

    def refresh_available_coupons(self):
        self.list_available.clear()
        base_amount = self.spin_amount.value()
        coupons = self.discount_service.get_available_coupons(base_amount)
        for coupon in coupons:
            if coupon.type == CouponType.DISCOUNT:
                desc = f"{coupon.name} - {coupon.discount_value}折 (满{coupon.min_consumption}元可用)"
            else:
                desc = f"{coupon.name} - 减{coupon.discount_value}元 (满{coupon.min_consumption}元可用)"
            item = QListWidgetItem(desc)
            item.setData(Qt.UserRole, coupon.id)
            item.setData(Qt.UserRole + 1, coupon)
            self.list_available.addItem(item)

    def get_selected_coupon_id(self):
        row = self.coupon_widget.currentRow()
        if row >= 0:
            return int(self.coupon_widget.item(row, 0).text())
        return None

    def add_coupon(self):
        dialog = CouponDialog(self)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.discount_service.create_coupon(**data)
                self.show_info("成功", "优惠券创建成功")
                self.refresh_coupons()
                self.refresh_available_coupons()
            except Exception as e:
                self.show_error("错误", str(e))

    def edit_coupon(self):
        coupon_id = self.get_selected_coupon_id()
        if not coupon_id:
            self.show_info("提示", "请选择要修改的优惠券")
            return
        coupon = self.discount_service.get_coupon(coupon_id)
        dialog = CouponDialog(self, coupon)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.discount_service.update_coupon(coupon_id, **data)
                self.show_info("成功", "优惠券修改成功")
                self.refresh_coupons()
                self.refresh_available_coupons()
            except Exception as e:
                self.show_error("错误", str(e))

    def delete_coupon(self):
        coupon_id = self.get_selected_coupon_id()
        if not coupon_id:
            self.show_info("提示", "请选择要删除的优惠券")
            return
        if self.show_confirm("确认", "确定要删除这个优惠券吗？"):
            if self.discount_service.delete_coupon(coupon_id):
                self.show_info("成功", "优惠券删除成功")
                self.refresh_coupons()
                self.refresh_available_coupons()
            else:
                self.show_error("错误", "删除失败")

    def edit_config(self):
        config = self.discount_service.get_discount_config()
        dialog = DiscountConfigDialog(self, config)
        if dialog.exec():
            try:
                data = dialog.get_data()
                self.discount_service.update_discount_config(**data)
                self.show_info("成功", "配置修改成功")
                self.refresh_config()
                self.calculate()
            except Exception as e:
                self.show_error("错误", str(e))

    def add_selected_coupon(self):
        for item in self.list_available.selectedItems():
            coupon_id = item.data(Qt.UserRole)
            if coupon_id not in self.selected_coupons:
                self.selected_coupons.append(coupon_id)
                new_item = QListWidgetItem(item.text())
                new_item.setData(Qt.UserRole, coupon_id)
                self.list_selected.addItem(new_item)
        self.calculate()

    def remove_selected_coupon(self):
        for item in self.list_selected.selectedItems():
            coupon_id = item.data(Qt.UserRole)
            if coupon_id in self.selected_coupons:
                self.selected_coupons.remove(coupon_id)
            row = self.list_selected.row(item)
            self.list_selected.takeItem(row)
        self.calculate()

    def clear_selected_coupons(self):
        self.selected_coupons.clear()
        self.list_selected.clear()
        self.calculate()

    def calculate(self):
        self.refresh_available_coupons()
        base_amount = self.spin_amount.value()
        if not self.selected_coupons:
            result_text = f"原始金额: ¥{base_amount:.2f}\n\n请选择优惠券后点击计算"
            self.result_text.setPlainText(result_text)
            return

        result = self.discount_service.calculate_discount(base_amount, coupon_ids=self.selected_coupons)

        lines = result.calculation_steps
        lines.append("")
        lines.append("=" * 50)
        lines.append(f"基础金额: ¥{result.base_amount:.2f}")
        lines.append(f"优惠金额: ¥{result.discount_amount:.2f}")
        lines.append(f"最终应付: ¥{result.final_amount:.2f}")
        if result.has_negative_protection:
            lines.append("⚠️ 已触发负值兜底校验")

        if result.applied_discounts:
            lines.append("")
            lines.append("优惠明细:")
            for d in result.applied_discounts:
                lines.append(f"  [{d['apply_order']}] {d['coupon_name']} ({d['coupon_type']}): -¥{d['applied_amount']:.2f}")

        self.result_text.setPlainText("\n".join(lines))
