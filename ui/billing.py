from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QTableWidgetItem,
                               QPushButton, QLabel, QGroupBox, QSplitter,
                               QComboBox, QDateEdit, QLineEdit, QCheckBox,
                               QTextEdit, QListWidget, QListWidgetItem,
                               QDoubleSpinBox, QSpinBox, QDialog, QInputDialog)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush, QFont
from ui.base_widget import BaseWidget, BaseDialog
from modules.bill_service import BillService
from modules.discount_service import DiscountService
from database.models import CouponType
from datetime import datetime, date
from datetime import date as py_date


class BillingDialog(BaseDialog):
    def __init__(self, parent=None, db=None, booking=None):
        self.db = db
        self.booking = booking
        self.selected_coupons = []
        self.current_result = None
        self.created_bill = None
        super().__init__("账单结算", parent)
        self.discount_service = DiscountService(db)
        self.bill_service = BillService(db)
        self.resize(700, 650)
        self._load_data()

    def init_dialog(self):
        main_layout = QVBoxLayout()

        info_group = QGroupBox("预订信息")
        info_layout = QFormLayout(info_group)
        self.lbl_table = QLabel("")
        self.lbl_customer = QLabel("")
        self.lbl_date = QLabel("")
        self.lbl_time = QLabel("")
        self.lbl_hours = QLabel("")
        self.lbl_base = QLabel("")
        self.lbl_base.setStyleSheet("font-size: 16px; font-weight: bold;")
        info_layout.addRow("桌号:", self.lbl_table)
        info_layout.addRow("客人:", self.lbl_customer)
        info_layout.addRow("日期:", self.lbl_date)
        info_layout.addRow("时间:", self.lbl_time)
        info_layout.addRow("时长:", self.lbl_hours)
        info_layout.addRow("基础金额:", self.lbl_base)
        main_layout.addWidget(info_group)

        coupon_group = QGroupBox("选择优惠券")
        coupon_layout = QVBoxLayout(coupon_group)

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

        coupon_layout.addWidget(list_splitter)

        btn_layout = QHBoxLayout()
        self.btn_add_coupon = QPushButton("→ 添加")
        self.btn_remove_coupon = QPushButton("← 移除")
        self.btn_clear_coupon = QPushButton("清空")
        self.btn_calc = QPushButton("🧮 计算")
        self.btn_add_coupon.clicked.connect(self.add_coupon)
        self.btn_remove_coupon.clicked.connect(self.remove_coupon)
        self.btn_clear_coupon.clicked.connect(self.clear_coupons)
        self.btn_calc.clicked.connect(self.calculate)
        btn_layout.addWidget(self.btn_add_coupon)
        btn_layout.addWidget(self.btn_remove_coupon)
        btn_layout.addWidget(self.btn_clear_coupon)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_calc)
        coupon_layout.addLayout(btn_layout)

        main_layout.addWidget(coupon_group)

        result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("font-family: Consolas, Monaco, monospace; font-size: 13px;")
        result_layout.addWidget(self.result_text)

        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("优惠合计:"))
        self.lbl_discount = QLabel("¥0.00")
        self.lbl_discount.setStyleSheet("font-size: 14px; color: #f44336; font-weight: bold;")
        amount_layout.addWidget(self.lbl_discount)
        amount_layout.addStretch()
        amount_layout.addWidget(QLabel("应付金额:"))
        self.lbl_final = QLabel("¥0.00")
        self.lbl_final.setStyleSheet("font-size: 18px; color: #1976d2; font-weight: bold;")
        amount_layout.addWidget(self.lbl_final)
        result_layout.addLayout(amount_layout)

        main_layout.addWidget(result_group)

        pay_group = QGroupBox("支付信息")
        pay_layout = QHBoxLayout(pay_group)
        pay_layout.addWidget(QLabel("支付方式:"))
        self.combo_payment = QComboBox()
        self.combo_payment.addItems(["现金", "微信支付", "支付宝", "银行卡", "会员卡", "其他"])
        self.combo_payment.setMinimumHeight(32)
        pay_layout.addWidget(self.combo_payment)
        pay_layout.addStretch()
        self.chk_print = QCheckBox("打印账单")
        self.chk_print.setChecked(True)
        pay_layout.addWidget(self.chk_print)
        main_layout.addWidget(pay_group)

        self.form_layout.addRow(main_layout)

    def _load_data(self):
        if not self.booking:
            self.show_error("错误", "预订信息不存在")
            return

        table = self.booking.table
        if not table:
            self.show_error("错误", "关联的麻将桌信息不存在")
            return

        self.lbl_table.setText(f"{table.table_number} - {table.name}")
        self.lbl_customer.setText(self.booking.customer_name)
        self.lbl_date.setText(str(self.booking.booking_date))
        time_str = f"{self.booking.start_time.strftime('%H:%M')}-{self.booking.end_time.strftime('%H:%M')}"
        self.lbl_time.setText(time_str)
        self.lbl_hours.setText(f"{self.booking.total_hours:.1f} 小时")
        self.lbl_base.setText(f"¥{self.booking.base_amount:.2f}")

        try:
            coupons = self.discount_service.get_available_coupons(self.booking.base_amount)
            for coupon in coupons:
                if coupon.type == CouponType.DISCOUNT:
                    desc = f"{coupon.name} - {coupon.discount_value}折 (满{coupon.min_consumption or 0}元)"
                else:
                    desc = f"{coupon.name} - 减{coupon.discount_value}元 (满{coupon.min_consumption or 0}元)"
                item = QListWidgetItem(desc)
                item.setData(Qt.UserRole, coupon.id)
                self.list_available.addItem(item)
        except Exception as e:
            pass

        self.calculate()

    def add_coupon(self):
        for item in self.list_available.selectedItems():
            coupon_id = item.data(Qt.UserRole)
            if coupon_id not in self.selected_coupons:
                self.selected_coupons.append(coupon_id)
                new_item = QListWidgetItem(item.text())
                new_item.setData(Qt.UserRole, coupon_id)
                self.list_selected.addItem(new_item)
        self.calculate()

    def remove_coupon(self):
        for item in self.list_selected.selectedItems():
            coupon_id = item.data(Qt.UserRole)
            if coupon_id in self.selected_coupons:
                self.selected_coupons.remove(coupon_id)
            row = self.list_selected.row(item)
            self.list_selected.takeItem(row)
        self.calculate()

    def clear_coupons(self):
        self.selected_coupons.clear()
        self.list_selected.clear()
        self.calculate()

    def calculate(self):
        if not self.booking:
            return
        try:
            result = self.discount_service.calculate_discount(
                self.booking.base_amount, coupon_ids=self.selected_coupons)

            lines = list(result.calculation_steps) if result.calculation_steps else []
            lines.append("")
            lines.append("=" * 50)
            lines.append(f"基础金额: ¥{result.base_amount:.2f}")
            lines.append(f"优惠金额: ¥{result.discount_amount:.2f}")
            lines.append(f"最终应付: ¥{result.final_amount:.2f}")
            if result.has_negative_protection:
                lines.append("⚠️ 已触发负值兜底校验，金额已调整为0")

            if result.applied_discounts:
                lines.append("")
                lines.append("优惠明细:")
                for d in result.applied_discounts:
                    lines.append(f"  [{d.get('apply_order', '?')}] {d.get('coupon_name', '')} ({d.get('coupon_type', '')}): -¥{d.get('applied_amount', 0):.2f}")

            self.result_text.setPlainText("\n".join(lines))
            self.lbl_discount.setText(f"-¥{result.discount_amount:.2f}")
            self.lbl_final.setText(f"¥{result.final_amount:.2f}")
            self.current_result = result
        except Exception as e:
            self.result_text.setPlainText(f"计算出错: {str(e)}")
            self.current_result = None

    def get_data(self):
        return {
            "payment_method": self.combo_payment.currentText(),
            "print": self.chk_print.isChecked()
        }

    def validate(self):
        if not self.booking:
            self.show_error("错误", "预订信息不存在")
            return False
        if not self.current_result:
            self.show_error("错误", "请先计算优惠金额")
            return False
        return True

    def accept(self):
        if not self.validate():
            return

        try:
            bill = self.bill_service.create_bill(
                booking_id=self.booking.id,
                discount_result=self.current_result
            )

            data = self.get_data()
            self.bill_service.pay_bill(bill.id, data["payment_method"])

            self.created_bill = bill

            if data["print"]:
                print_content = self.bill_service.generate_print_content(bill.id)
                try:
                    from PySide6.QtPrintSupport import QPrinter, QPrintDialog
                    from PySide6.QtGui import QTextDocument

                    printer = QPrinter(QPrinter.HighResolution)
                    printer.setPageSize(QPrinter.A4)
                    printer.setOutputFormat(QPrinter.NativeFormat)
                    dialog = QPrintDialog(printer, self)
                    if dialog.exec() == QDialog.Accepted:
                        doc = QTextDocument()
                        doc.setPlainText(print_content)
                        doc.print_(printer)
                except ImportError:
                    pass
                except Exception:
                    pass

            self.show_info("成功", f"账单已生成并支付成功！\n账单号: {bill.bill_no}\n应付: ¥{bill.final_amount:.2f}")
            super().accept()
        except Exception as e:
            self.show_error("错误", str(e))
            return


class BillingWidget(BaseWidget):
    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.bill_service = BillService(self.db)
        self.discount_service = DiscountService(self.db)
        self.refresh()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("📄 账单管理")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1976d2;")
        main_layout.addWidget(title)

        splitter = QSplitter(Qt.Vertical)

        filter_group = QGroupBox("查询条件")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("开始日期:"))
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.setDate(QDate.currentDate().addDays(-7))
        self.date_start.dateChanged.connect(self.refresh)
        filter_layout.addWidget(self.date_start)

        filter_layout.addWidget(QLabel("结束日期:"))
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.setDate(QDate.currentDate())
        self.date_end.dateChanged.connect(self.refresh)
        filter_layout.addWidget(self.date_end)

        self.chk_only_unpaid = QCheckBox("仅显示未支付")
        self.chk_only_unpaid.toggled.connect(self.refresh)
        filter_layout.addWidget(self.chk_only_unpaid)

        self.btn_refresh = self.create_button("🔄 刷新", callback=self.refresh)
        filter_layout.addWidget(self.btn_refresh)

        filter_layout.addStretch()

        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet("font-weight: bold; color: #666;")
        filter_layout.addWidget(self.lbl_stats)

        main_layout.addWidget(filter_group)

        bill_group = QGroupBox("账单列表")
        bill_layout = QVBoxLayout(bill_group)

        btn_layout = QHBoxLayout()
        self.btn_view = self.create_button("👁️ 查看详情", callback=self.view_bill)
        self.btn_print = self.create_button("🖨️ 打印", callback=self.print_bill)
        self.btn_pay = self.create_button("💰 支付", callback=self.pay_bill)
        self.btn_delete = self.create_button("🗑️ 删除", callback=self.delete_bill)
        btn_layout.addWidget(self.btn_view)
        btn_layout.addWidget(self.btn_print)
        btn_layout.addWidget(self.btn_pay)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()
        bill_layout.addLayout(btn_layout)

        self.bill_widget = self.create_table([
            "ID", "账单号", "桌号", "客人", "日期", "基础金额", "优惠金额", "应付金额", "支付方式", "状态"
        ])
        bill_layout.addWidget(self.bill_widget)

        splitter.addWidget(bill_group)

        detail_group = QGroupBox("账单详情")
        detail_layout = QVBoxLayout(detail_group)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet("font-family: Consolas, Monaco, monospace; font-size: 12px;")
        detail_layout.addWidget(self.detail_text)
        splitter.addWidget(detail_group)

        splitter.setSizes([400, 250])
        main_layout.addWidget(splitter)

        self.bill_widget.itemSelectionChanged.connect(self.on_bill_selected)

    def refresh(self):
        self.refresh_bills()
        self.on_bill_selected()

    def refresh_bills(self):
        self.clear_table(self.bill_widget)
        start_date = self.date_start.date().toPython()
        end_date = self.date_end.date().toPython()
        only_unpaid = self.chk_only_unpaid.isChecked()
        bills = self.bill_service.get_all_bills(start_date, end_date, only_unpaid)

        total_base = 0
        total_discount = 0
        total_final = 0
        total_paid = 0

        for bill in bills:
            row = self.bill_widget.rowCount()
            self.bill_widget.insertRow(row)

            status = "已支付" if bill.is_paid else "未支付"
            payment_method = bill.payment_method or "-"
            created_date = bill.created_at.strftime('%Y-%m-%d %H:%M') if bill.created_at else ""

            self.set_table_row(self.bill_widget, row, [
                bill.id, bill.bill_no, bill.table_number, bill.customer_name,
                created_date, f"¥{bill.base_amount:.2f}", f"¥{bill.discount_amount:.2f}",
                f"¥{bill.final_amount:.2f}", payment_method, status
            ])

            status_item = self.bill_widget.item(row, 9)
            if bill.is_paid:
                status_item.setForeground(QBrush(QColor("#4caf50")))
            else:
                status_item.setForeground(QBrush(QColor("#f44336")))

            total_base += bill.base_amount
            total_discount += bill.discount_amount
            total_final += bill.final_amount
            if bill.is_paid:
                total_paid += bill.final_amount

        self.lbl_stats.setText(
            f"共 {len(bills)} 笔 | 营业额: ¥{total_base:.2f} | 优惠: ¥{total_discount:.2f} | 实收: ¥{total_paid:.2f}"
        )

    def on_bill_selected(self):
        bill_id = self.get_selected_bill_id()
        self.detail_text.clear()
        if bill_id:
            content = self.bill_service.generate_print_content(bill_id)
            self.detail_text.setPlainText(content)

    def get_selected_bill_id(self):
        row = self.bill_widget.currentRow()
        if row >= 0:
            return int(self.bill_widget.item(row, 0).text())
        return None

    def view_bill(self):
        bill_id = self.get_selected_bill_id()
        if not bill_id:
            self.show_info("提示", "请选择要查看的账单")
            return
        content = self.bill_service.generate_print_content(bill_id)
        dialog = QDialog(self)
        dialog.setWindowTitle("账单详情")
        dialog.setModal(True)
        dialog.resize(450, 600)
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(content)
        text_edit.setStyleSheet("font-family: Consolas, Monaco, monospace;")
        layout.addWidget(text_edit)
        dialog.exec()

    def print_bill(self):
        bill_id = self.get_selected_bill_id()
        if not bill_id:
            self.show_info("提示", "请选择要打印的账单")
            return

        try:
            content = self.bill_service.generate_print_content(bill_id)
            from PySide6.QtPrintSupport import QPrinter, QPrintDialog
            from PySide6.QtGui import QTextDocument

            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPrinter.A4)
            printer.setOutputFormat(QPrinter.NativeFormat)
            dialog = QPrintDialog(printer, self)
            if dialog.exec() == QDialog.Accepted:
                doc = QTextDocument()
                doc.setPlainText(content)
                doc.print_(printer)
                self.show_info("成功", "账单已发送打印")
        except ImportError:
            self.show_info("提示", "打印功能需要安装 PySide6 的打印支持模块")
        except Exception as e:
            self.show_error("错误", str(e))

    def pay_bill(self):
        bill_id = self.get_selected_bill_id()
        if not bill_id:
            self.show_info("提示", "请选择要支付的账单")
            return

        bill = self.bill_service.get_bill(bill_id)
        if bill and bill.is_paid:
            self.show_info("提示", "该账单已支付")
            return

        payment_methods = ["现金", "微信支付", "支付宝", "银行卡", "会员卡", "其他"]
        method, ok = QInputDialog.getItem(self, "选择支付方式", "请选择支付方式:", payment_methods, 0, False)
        if ok:
            if self.bill_service.pay_bill(bill_id, method):
                self.show_info("成功", "支付成功")
                self.refresh()
            else:
                self.show_error("错误", "支付失败")

    def delete_bill(self):
        bill_id = self.get_selected_bill_id()
        if not bill_id:
            self.show_info("提示", "请选择要删除的账单")
            return
        if self.show_confirm("确认", "确定要删除这个账单吗？"):
            if self.bill_service.delete_bill(bill_id):
                self.show_info("成功", "账单删除成功")
                self.refresh()
            else:
                self.show_error("错误", "删除失败")
