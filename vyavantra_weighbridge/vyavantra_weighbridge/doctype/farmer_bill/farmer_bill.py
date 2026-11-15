# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from vyavantra_weighbridge.billing import SlipBill
from vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip import get_rate_master_rates


class FarmerBill(SlipBill):
	party_field = "farmer"
	slip_party_field = "farmer"
	flag_field = "farmer_bill"
	slip_rate_field = "cane_rate"

	def validate(self):
		# During submit Frappe sets docstatus=1 before validation; the draft still needs its final
		# amount calculated. A previously submitted bill has immutable monetary rows.
		if self.docstatus == 1 and self.get("_action") != "submit":
			return
		super().validate()
		if self.docstatus == 0:
			self.approval_status = "Draft"

	def before_submit(self):
		if not ({"Accounts Manager", "Weighbridge Manager", "System Manager"} & set(frappe.get_roles())):
			frappe.throw(_("Only Accounts Manager or Weighbridge Manager can approve a Farmer Bill"))
		if not self.slips:
			frappe.throw(_("No weighment slips to bill. Use 'Fetch Weighment Slips'."))
		for row in self.slips:
			slip = frappe.db.get_value("Weighment Slip", row.slip, ["docstatus", "farmer_bill", "farmer"], as_dict=True)
			if not slip or slip.docstatus != 1:
				frappe.throw(_("Row {0}: Weighment Slip {1} is not submitted").format(row.idx, row.slip))
			if slip.farmer_bill and slip.farmer_bill != self.name:
				frappe.throw(_("Row {0}: Weighment Slip {1} is already billed in {2}").format(row.idx, row.slip, slip.farmer_bill))
			if str(slip.farmer) != str(self.farmer):
				frappe.throw(_("Row {0}: Weighment Slip {1} belongs to another farmer").format(row.idx, row.slip))

	def on_submit(self):
		super().on_submit()
		self.db_set("approval_status", "Approved", update_modified=False)

	def set_payment_status(self):
		if self.docstatus == 0:
			self.payment_status = "Draft"
		elif flt(self.paid_amount) > 0 and flt(self.outstanding_amount) <= 0:
			self.payment_status = "Paid"
		else:
			self.payment_status = "Unpaid"

	def calculate(self):
		"""Use each slip's final kilograms and its effective-dated cane rate.

		The deduction is informational: final net kilograms already exclude binding and other weight
		deductions, so subtracting their monetary value again would underpay the farmer.
		"""
		self.total_cane_weight = self.total_net_weight = 0
		self.total_quantity = self.total_amount = self.total_deductions = 0
		for row in self.slips:
			self.set_row_rate(row)
			row.quantity = flt(flt(row.net_weight) / 1000, 3)
			row.amount = flt(row.quantity * flt(row.rate), 2)
			self.total_cane_weight += flt(row.cane_weight)
			self.total_net_weight += flt(row.net_weight)
			self.total_quantity += row.quantity
			self.total_amount += row.amount
		self.total_quantity = flt(self.total_quantity, 3)
		self.total_amount = flt(self.total_amount, 2)
		self.compute_net()
		self.outstanding_amount = flt(self.net_payable - flt(self.paid_amount), 2)

	def compute_net(self):
		# Weights already include the binding and other deductions; they must never be subtracted
		# from the amount a second time. This is the monetary value of the deducted kilograms.
		self.total_deductions = flt(
			sum((flt(row.cane_weight) - flt(row.net_weight)) / 1000 * flt(row.rate) for row in self.slips), 2
		)
		self.net_payable = flt(self.total_amount, 2)

	def set_row_rate(self, row):
		if not row.slip or (self.docstatus == 1 and self.get("_action") != "submit"):
			return
		slip = frappe.db.get_value(
			"Weighment Slip", row.slip,
			["slip_date", "delivery_type", "vehicle_no", "village", "cane_weight", "mat_weight",
			 "net_after_binding", "other_deduction_percent", "other_deduction", "net_cane_weight"],
			as_dict=True,
		)
		if not slip:
			frappe.throw(_("Weighment Slip {0} does not exist").format(row.slip))
		row.slip_date = slip.slip_date
		row.delivery_type = slip.delivery_type
		row.vehicle = slip.vehicle_no
		row.village = slip.village
		row.cane_weight = slip.cane_weight
		row.mat_weight = slip.mat_weight
		row.net_after_binding = slip.net_after_binding
		row.other_deduction_percent = slip.other_deduction_percent
		row.other_deduction = slip.other_deduction
		row.net_weight = slip.net_cane_weight
		# Use each slip's effective date and delivery type, not the bill date.
		rates = get_rate_master_rates(slip.slip_date, slip.delivery_type)
		if not rates:
			frappe.throw(_("No Cane Rate Master for {0} on {1}").format(slip.delivery_type, slip.slip_date))
		row.rate = rates["cane_rate"]

	@frappe.whitelist()
	def fetch_slips(self):
		party = self.farmer
		if not (party and self.from_date and self.to_date):
			frappe.throw(_("Select the farmer, From Date and To Date first"))
		slips = frappe.get_all(
			"Weighment Slip",
			filters={"docstatus": 1, "farmer": party, "slip_date": ["between", [self.from_date, self.to_date]],
			         "farmer_bill": ["is", "not set"]},
			fields=["name"], order_by="slip_date, serial_no, name",
		)
		self.set("slips", [])
		for slip in slips:
			self.append("slips", {"slip": slip.name})
		self.calculate()
		if not slips:
			frappe.msgprint(_("No unbilled, submitted weighment slips found for the selected period."))
		return len(slips)

	def apply_payment(self, amount):
		if self.docstatus != 1 or self.approval_status != "Approved":
			frappe.throw(_("Approve the Farmer Bill before paying"))
		paid = flt(flt(self.paid_amount) + flt(amount), 2)
		outstanding = flt(flt(self.net_payable) - paid, 2)
		if paid < 0 or outstanding < 0:
			frappe.throw(_("Payment would exceed the net payable amount of {0}").format(self.name))
		self.db_set({"paid_amount": paid, "outstanding_amount": outstanding,
		             "payment_status": "Paid" if outstanding <= 0 else "Unpaid"})
