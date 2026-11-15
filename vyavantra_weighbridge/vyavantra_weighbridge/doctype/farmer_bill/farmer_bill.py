# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from vyavantra_weighbridge.billing import SlipBill
from vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip import (
	get_rate_master_rates,
	round_kg,
)

CANE_SUPPLIER_GROUP = "Cane Supplier"


def whole_rupees(value):
	"""The amount to the nearest rupee, half rounded up."""
	return flt(round_kg(value))


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

	# --- payment: Unpaid -> Paid books a Payment Entry, Paid -> Unpaid cancels it -------------------
	def before_update_after_submit(self):
		before = self.get_doc_before_save()
		was_paid = bool(before and before.workflow_status == "Paid")
		if self.workflow_status == "Paid" and not was_paid and not (self.reference_no and self.reference_date):
			frappe.throw(_("Enter the Reference No and Reference Date of the bank payment, save, and then mark the bill Paid"))
		if was_paid and self.workflow_status == "Paid" and (
			self.reference_no != before.reference_no or str(self.reference_date) != str(before.reference_date)
		):
			frappe.throw(_("The payment reference of a Paid bill cannot be changed. Use Cancel Payment first."))

	def on_update_after_submit(self):
		before = self.get_doc_before_save()
		was_paid = bool(before and before.workflow_status == "Paid")
		if self.workflow_status == "Paid" and not was_paid:
			self.make_payment_entry()
		elif was_paid and self.workflow_status == "Unpaid":
			self.cancel_payment_entry()

	def make_payment_entry(self):
		"""Book the cane purchase against the farmer and pay it from the bank, both on the Reference Date.

		ERPNext only lets a party sit on a Payable account, so the bank cannot pay the purchase account directly:
		a Journal Entry books Cane Purchase -> farmer payable, and the Payment Entry pays that payable from the bank.
		"""
		from erpnext.accounts.party import get_party_account

		if self.payment_entry:
			frappe.throw(_("Payment Entry {0} already exists for this bill").format(self.payment_entry))
		settings = frappe.get_cached_doc("Weighbridge Settings")
		if not (settings.company and settings.bank_account and settings.cane_purchase_account):
			frappe.throw(_("Set the Company, Bank Account and Cane Purchase Account in Weighbridge Settings first"))
		amount = whole_rupees(self.total_amount)
		supplier = get_or_create_supplier(self.farmer)
		payable = get_party_account("Supplier", supplier, settings.company)
		cost_center = frappe.get_cached_value("Company", settings.company, "cost_center")
		remarks = _("Farmer Bill {0} ({1} to {2}), farmer {3} - {4}").format(
			self.name, self.from_date, self.to_date, self.farmer, self.farmer_name
		)

		purchase = frappe.new_doc("Journal Entry")
		purchase.update({
			"voucher_type": "Journal Entry",
			"company": settings.company,
			"posting_date": self.reference_date,
			"user_remark": _("Cane purchase: {0}").format(remarks),
		})
		purchase.append("accounts", {
			"account": settings.cane_purchase_account, "cost_center": cost_center, "debit_in_account_currency": amount,
		})
		purchase.append("accounts", {
			"account": payable, "party_type": "Supplier", "party": supplier, "credit_in_account_currency": amount,
		})

		entry = frappe.new_doc("Payment Entry")
		entry.update({
			"payment_type": "Pay",
			"company": settings.company,
			"posting_date": self.reference_date,
			"party_type": "Supplier",
			"party": supplier,
			"paid_from": settings.bank_account,
			"paid_to": payable,
			"paid_amount": amount,
			"received_amount": amount,
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"reference_no": self.reference_no,
			"reference_date": self.reference_date,
			"cost_center": cost_center,
			"custom_remarks": 1,
			"remarks": _("Cane payment: {0}").format(remarks),
		})
		# whoever may mark the bill Paid books its payment, with or without a role on the accounting documents
		for doc in (purchase, entry):
			doc.flags.ignore_permissions = True
		purchase.insert()
		purchase.submit()
		entry.append("references", {
			"reference_doctype": "Journal Entry", "reference_name": purchase.name, "allocated_amount": amount,
		})
		entry.insert()
		entry.submit()
		self.db_set({"journal_entry": purchase.name, "payment_entry": entry.name, "paid_amount": amount,
		             "outstanding_amount": 0, "payment_status": "Paid"})

	def cancel_payment_entry(self):
		# the payment goes first: it is allocated against the purchase entry
		for doctype, field in (("Payment Entry", "payment_entry"), ("Journal Entry", "journal_entry")):
			name = self.get(field)
			if name and frappe.db.get_value(doctype, name, "docstatus") == 1:
				doc = frappe.get_doc(doctype, name)
				# both are cancelled from their own bill, which is the document linked to them
				doc.flags.ignore_links = True
				doc.flags.ignore_permissions = True
				doc.cancel()
		self.db_set({"payment_entry": None, "journal_entry": None, "paid_amount": 0,
		             "outstanding_amount": flt(self.net_payable, 2), "payment_status": "Unpaid"})

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
		# the farmer is paid in whole rupees; Round Off is what that added to or took off the sum of the rows
		exact = flt(self.total_amount, 2)
		self.total_amount = whole_rupees(exact)
		self.round_off = flt(self.total_amount - exact, 2)
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
			["slip_date", "delivery_type", "vehicle_no", "village", "route", "cane_weight", "mat_weight",
			 "net_after_binding", "other_deduction_percent", "other_deduction", "net_cane_weight"],
			as_dict=True,
		)
		if not slip:
			frappe.throw(_("Weighment Slip {0} does not exist").format(row.slip))
		row.slip_date = slip.slip_date
		row.delivery_type = slip.delivery_type
		row.vehicle = slip.vehicle_no
		row.village = slip.village
		row.route = slip.route
		row.cane_weight = slip.cane_weight
		row.gross_quantity = flt(flt(slip.cane_weight) / 1000, 3)
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


def get_or_create_supplier(cane_supplier):
	"""The Supplier a farmer's payments are booked against; made from the Cane Supplier the first time."""
	farmer = frappe.db.get_value("Cane Supplier", cane_supplier, ["supplier", "farmer_name"], as_dict=True)
	if not farmer:
		frappe.throw(_("Cane Supplier {0} does not exist").format(cane_supplier))
	if farmer.supplier:
		return farmer.supplier

	if not frappe.db.exists("Supplier Group", CANE_SUPPLIER_GROUP):
		root = frappe.db.get_value("Supplier Group", {"is_group": 1, "parent_supplier_group": ["in", ["", None]]})
		frappe.get_doc({
			"doctype": "Supplier Group", "supplier_group_name": CANE_SUPPLIER_GROUP, "parent_supplier_group": root,
		}).insert(ignore_permissions=True)

	# Suppliers are named by their name: a second farmer of the same name carries his farmer number
	supplier_name = (farmer.farmer_name or "").strip() or str(cane_supplier)
	if frappe.db.exists("Supplier", supplier_name) or frappe.db.exists("Supplier", {"supplier_name": supplier_name}):
		supplier_name = f"{supplier_name} - {cane_supplier}"
	supplier = frappe.get_doc({
		"doctype": "Supplier", "supplier_name": supplier_name, "supplier_group": CANE_SUPPLIER_GROUP,
		"supplier_type": "Individual",
	}).insert(ignore_permissions=True)
	frappe.db.set_value("Cane Supplier", cane_supplier, "supplier", supplier.name, update_modified=False)
	return supplier.name
