# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

"""Shared logic for Farmer / Tractor / Todani / Agent bills built from weighment slips."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

BILL_DOCTYPES = ("Farmer Bill", "Tractor Contractor Bill", "Todani Contractor Bill", "Agent Bill")


class SlipBill(Document):
	# --- configuration, overridden by each bill doctype -------------------------------
	party_field = None  # field on the bill holding the party
	slip_party_field = None  # field on the weighment slip holding the same party
	flag_field = None  # field on the weighment slip that links back to this bill
	slip_rate_field = None  # weighment slip field holding the per-ton rate
	party_doctype = None
	balance_deductions = ()  # (bill field, party balance field) pairs reduced on submit
	party_name_field = None  # party master field holding the party's name
	supplier_group = None  # Supplier Group of the Suppliers made for this bill's parties

	# --- lifecycle --------------------------------------------------------------------
	def validate(self):
		if self.from_date and self.to_date and self.from_date > self.to_date:
			frappe.throw(_("From Date cannot be after To Date"))
		self.validate_party()
		self.calculate()
		if self.docstatus == 0:
			self.paid_amount = 0
		self.set_payment_status()

	def validate_party(self):
		pass

	def before_submit(self):
		if not self.slips:
			frappe.throw(_("No weighment slips to bill. Use 'Fetch Weighment Slips'."))
		self.check_balances()
		if flt(self.net_payable) < 0:
			frappe.throw(_("Net Payable cannot be negative. Reduce the deductions."))
		for row in self.slips:
			slip = frappe.db.get_value(
				"Weighment Slip", row.slip, ["docstatus", self.flag_field, self.slip_party_field], as_dict=True
			)
			if not slip or slip.docstatus != 1:
				frappe.throw(_("Row {0}: Weighment Slip {1} is not submitted").format(row.idx, row.slip))
			if slip.get(self.flag_field) and slip.get(self.flag_field) != self.name:
				frappe.throw(
					_("Row {0}: Weighment Slip {1} is already billed in {2}").format(
						row.idx, row.slip, slip.get(self.flag_field)
					)
				)
			if slip.get(self.slip_party_field) != self.get(self.party_field):
				frappe.throw(_("Row {0}: Weighment Slip {1} belongs to another party").format(row.idx, row.slip))

	def on_submit(self):
		for row in self.slips:
			frappe.db.set_value("Weighment Slip", row.slip, self.flag_field, self.name, update_modified=False)
		self.adjust_balances(-1)

	def on_cancel(self):
		if flt(self.paid_amount):
			frappe.throw(_("Cancel the payments made against this bill first"))
		for row in self.slips:
			if frappe.db.get_value("Weighment Slip", row.slip, self.flag_field) == self.name:
				frappe.db.set_value("Weighment Slip", row.slip, self.flag_field, None, update_modified=False)
		self.adjust_balances(1)

	# --- calculation ------------------------------------------------------------------
	def calculate(self):
		total_qty = total_amount = total_farakt = 0.0
		for row in self.slips:
			row.quantity = flt(row.net_weight) / 1000
			self.set_row_rate(row)
			row.amount = flt(row.quantity * flt(row.rate), 2)
			row.farakt_amount = flt(row.quantity * flt(row.farakt_rate), 2)
			total_qty += row.quantity
			total_amount += row.amount
			total_farakt += row.farakt_amount
		self.total_quantity = flt(total_qty, 3)
		self.total_amount = flt(total_amount, 2)
		if self.meta.has_field("farakt_amount"):
			self.farakt_amount = flt(total_farakt, 2)
		self.compute_net()
		self.outstanding_amount = flt(flt(self.net_payable) - flt(self.paid_amount), 2)

	def set_row_rate(self, row):
		pass

	def compute_net(self):
		raise NotImplementedError

	def set_payment_status(self):
		if self.docstatus == 0 or not flt(self.paid_amount):
			self.payment_status = "Unpaid"
		elif flt(self.outstanding_amount) <= 0:
			self.payment_status = "Paid"
		else:
			self.payment_status = "Partly Paid"

	# --- slips ------------------------------------------------------------------------
	@frappe.whitelist()
	def fetch_slips(self):
		party = self.get(self.party_field)
		if not (party and self.from_date and self.to_date):
			frappe.throw(_("Select the party, From Date and To Date first"))
		slips = frappe.get_all(
			"Weighment Slip",
			filters={
				"docstatus": 1,
				self.slip_party_field: party,
				"slip_date": ["between", [self.from_date, self.to_date]],
				self.flag_field: ["is", "not set"],
			},
			fields=["name", "slip_date", "vehicle_no", "village", "net_cane_weight", "cane_rate",
					"transport_rate", "todani_rate", "farakt_rate"],
			order_by="slip_date, serial_no, name",
		)
		self.set("slips", [])
		for s in slips:
			self.append("slips", {
				"slip": s.name, "slip_date": s.slip_date, "vehicle": s.vehicle_no, "village": s.village,
				"net_weight": s.net_cane_weight, "rate": self.slip_rate(s),
				"farakt_rate": s.farakt_rate if self.meta.has_field("farakt_amount") else 0,
			})
		self.calculate()
		if not slips:
			frappe.msgprint(_("No unbilled, submitted weighment slips found for the selected period."))
		return len(slips)

	def slip_rate(self, slip):
		return flt(slip.get(self.slip_rate_field))

	# --- advance / deposit balances ---------------------------------------------------
	def check_balances(self):
		if not self.balance_deductions:
			return
		party = self.get(self.party_field)
		for bill_field, bal_field in self.balance_deductions:
			ded = flt(self.get(bill_field))
			if ded < 0:
				frappe.throw(_("{0} cannot be negative").format(self.meta.get_label(bill_field)))
			bal = flt(frappe.db.get_value(self.party_doctype, party, bal_field))
			if ded > bal:
				frappe.throw(
					_("{0} of {1} exceeds the available balance of {2}").format(
						self.meta.get_label(bill_field), ded, bal
					)
				)

	def adjust_balances(self, sign):
		party = self.get(self.party_field)
		for bill_field, bal_field in self.balance_deductions:
			ded = flt(self.get(bill_field))
			if ded:
				frappe.db.sql(
					f"update `tab{self.party_doctype}` set `{bal_field}` = `{bal_field}` + %s where name = %s",
					(sign * ded, party),
				)

	# --- payment through the workflow: Unpaid (saved) -> Pay -> Paid (submitted) ----------------
	def before_insert(self):
		if not self.meta.has_field("paid_from"):
			return
		for field, value in get_payment_defaults(self.doctype).items():
			if value and not self.get(field):
				self.set(field, value)

	def payment_amount(self):
		return flt(self.net_payable, 2)

	def validate_payment_details(self):
		"""Everything Pay needs is chosen on the bill itself: company, the two accounts and the bank reference."""
		labels = [self.meta.get_label(f) for f in ("company", "paid_from", "paid_to", "reference_no", "reference_date")
		          if not self.get(f)]
		if labels:
			frappe.throw(_("Fill these before Pay: {0}").format(", ".join(labels)))
		if self.payment_amount() <= 0:
			frappe.throw(_("There is nothing to pay on this bill"))
		for field, party_types in (("paid_from", ()), ("paid_to", ("Receivable", "Payable"))):
			account = frappe.db.get_value("Account", self.get(field), ["company", "is_group", "account_type"], as_dict=True)
			label = self.meta.get_label(field)
			if account.company != self.company:
				frappe.throw(_("{0}: account {1} does not belong to {2}").format(label, self.get(field), self.company))
			if account.is_group:
				frappe.throw(_("{0}: {1} is a group account; choose a ledger account").format(label, self.get(field)))
			if account.account_type in party_types:
				frappe.throw(_("{0}: {1} is a party account; choose the expense account the bill is booked to").format(
					label, self.get(field)))

	def book_payment(self):
		"""Book the purchase against the party and pay it from the bank, both on the Reference Date.

		ERPNext only lets a party sit on a Payable account, so the bank cannot pay the expense account directly:
		a Journal Entry books Paid To -> party payable, and the Payment Entry pays that payable from Paid From.
		"""
		from erpnext.accounts.party import get_party_account

		amount = self.payment_amount()
		party = self.get(self.party_field)
		supplier = get_or_create_supplier(self.party_doctype, party, self.party_name_field, self.supplier_group)
		payable = get_party_account("Supplier", supplier, self.company)
		cost_center = frappe.get_cached_value("Company", self.company, "cost_center")
		remarks = _("{0} {1} ({2} to {3}), {4} - {5}").format(
			_(self.doctype), self.name, self.from_date, self.to_date, party,
			frappe.db.get_value(self.party_doctype, party, self.party_name_field),
		)

		purchase = frappe.new_doc("Journal Entry")
		purchase.update({
			"voucher_type": "Journal Entry", "company": self.company, "posting_date": self.reference_date,
			"user_remark": remarks,
		})
		purchase.append("accounts", {
			"account": self.paid_to, "cost_center": cost_center, "debit_in_account_currency": amount,
		})
		purchase.append("accounts", {
			"account": payable, "party_type": "Supplier", "party": supplier, "credit_in_account_currency": amount,
		})

		entry = frappe.new_doc("Payment Entry")
		entry.update({
			"payment_type": "Pay", "company": self.company, "posting_date": self.reference_date,
			"party_type": "Supplier", "party": supplier,
			"paid_from": self.paid_from, "paid_to": payable,
			"paid_amount": amount, "received_amount": amount,
			"source_exchange_rate": 1, "target_exchange_rate": 1,
			"reference_no": self.reference_no, "reference_date": self.reference_date,
			"cost_center": cost_center, "custom_remarks": 1, "remarks": remarks,
		})
		# whoever may Pay the bill books its payment, with or without a role on the accounting documents
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

	def cancel_payment(self):
		# the payment goes first: it is allocated against the purchase entry
		for doctype, field in (("Payment Entry", "payment_entry"), ("Journal Entry", "journal_entry")):
			name = self.get(field)
			if name and frappe.db.get_value(doctype, name, "docstatus") == 1:
				doc = frappe.get_doc(doctype, name)
				# both are cancelled from their own bill, which is the document linked to them
				doc.flags.ignore_links = True
				doc.flags.ignore_permissions = True
				doc.cancel()
		self.db_set({"paid_amount": 0, "outstanding_amount": flt(self.net_payable, 2), "payment_status": "Unpaid"})

	# --- payments ---------------------------------------------------------------------
	def apply_payment(self, amount):
		"""Called by Weighbridge Payment on submit (+) / cancel (-)."""
		paid = flt(flt(self.paid_amount) + flt(amount), 2)
		outstanding = flt(flt(self.net_payable) - paid, 2)
		if paid < 0 or outstanding < 0:
			frappe.throw(_("Payment would exceed the net payable amount of {0}").format(self.name))
		status = "Paid" if outstanding <= 0 else ("Partly Paid" if paid else "Unpaid")
		self.db_set({"paid_amount": paid, "outstanding_amount": outstanding, "payment_status": status})


@frappe.whitelist()
def get_payment_defaults(doctype):
	"""What a new bill starts with, from Weighbridge Settings. Each can be changed on the bill before Pay."""
	settings = frappe.get_cached_doc("Weighbridge Settings")
	return {
		"company": settings.company,
		"paid_from": settings.bank_account,
		"paid_to": settings.cane_purchase_account if doctype == "Farmer Bill" else None,
	}


def get_or_create_supplier(party_doctype, party, name_field, supplier_group):
	"""The Supplier a party's payments are booked against; made from the party master the first time."""
	master = frappe.db.get_value(party_doctype, party, ["supplier", name_field], as_dict=True)
	if not master:
		frappe.throw(_("{0} {1} does not exist").format(_(party_doctype), party))
	if master.supplier:
		return master.supplier

	if not frappe.db.exists("Supplier Group", supplier_group):
		root = frappe.db.get_value("Supplier Group", {"is_group": 1, "parent_supplier_group": ["in", ["", None]]})
		frappe.get_doc({
			"doctype": "Supplier Group", "supplier_group_name": supplier_group, "parent_supplier_group": root,
		}).insert(ignore_permissions=True)

	# Suppliers are named by their name: a second party of the same name carries its own number
	supplier_name = (master.get(name_field) or "").strip() or str(party)
	if frappe.db.exists("Supplier", supplier_name) or frappe.db.exists("Supplier", {"supplier_name": supplier_name}):
		supplier_name = f"{supplier_name} - {party}"
	supplier = frappe.get_doc({
		"doctype": "Supplier", "supplier_name": supplier_name, "supplier_group": supplier_group,
		"supplier_type": "Individual",
	}).insert(ignore_permissions=True)
	frappe.db.set_value(party_doctype, party, "supplier", supplier.name, update_modified=False)
	return supplier.name
