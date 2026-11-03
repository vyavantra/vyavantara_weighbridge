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

	# --- payments ---------------------------------------------------------------------
	def apply_payment(self, amount):
		"""Called by Weighbridge Payment on submit (+) / cancel (-)."""
		paid = flt(flt(self.paid_amount) + flt(amount), 2)
		outstanding = flt(flt(self.net_payable) - paid, 2)
		if paid < 0 or outstanding < 0:
			frappe.throw(_("Payment would exceed the net payable amount of {0}").format(self.name))
		status = "Paid" if outstanding <= 0 else ("Partly Paid" if paid else "Unpaid")
		self.db_set({"paid_amount": paid, "outstanding_amount": outstanding, "payment_status": status})
