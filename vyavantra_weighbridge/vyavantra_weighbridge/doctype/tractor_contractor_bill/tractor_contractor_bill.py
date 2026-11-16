# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

from vyavantra_weighbridge.billing import SlipBill
from vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip import get_rate_master_rates

DEPOSIT_PERCENT = 10


class TractorContractorBill(SlipBill):
	"""Transport bill of a tractor contractor.

	Each weighment slip is paid at the Todani Rate of its delivery type. Diesel issued to the contractor is
	recovered at the rate of its own issue date: diesel issued against a slip sits on that slip's row, diesel
	issued on its own gets a row of its own. A deposit of 10% of the Total Amount is held back, and part of the
	contractor's outstanding advance can be recovered. A commission, a percentage of the Total Amount, is added.
	"""

	party_field = "contractor"
	slip_party_field = "transport_contractor"
	flag_field = "tractor_bill"
	party_doctype = "Contractor Master"
	# these fields ACCUMULATE on submit (sign=+1); reversed on cancel (sign=-1)
	balance_deductions = (
		("advance_deduction", "advance_balance"),
		("deposit_deduction", "deposit_balance"),
		("commission", "total_commission"),
	)
	party_name_field = "contractor_name"
	supplier_group = "Transport Contractor"
	allowed_types = ("Tractor Contractor", "Tractor / Cutting Contractor")

	def validate(self):
		# a submitted bill keeps the rates and quantities it was approved with
		if self.docstatus == 1 and self.get("_action") != "submit":
			return
		super().validate()

	def check_balances(self):
		"""Advance deduction cannot exceed outstanding (total_given - already_recovered). Deposit has no cap."""
		if flt(self.advance_deduction) < 0:
			frappe.throw(_("Advance Deduction cannot be negative"))
		if flt(self.advance_deduction) > flt(self.outstanding_advance):
			frappe.throw(_("Advance Deduction {0} is more than the Outstanding Advance {1}").format(
				frappe.format(self.advance_deduction, {"fieldtype": "Currency"}),
				frappe.format(self.outstanding_advance, {"fieldtype": "Currency"})))

	def validate_party(self):
		ctype = frappe.db.get_value("Contractor Master", self.contractor, "contractor_type")
		if ctype not in self.allowed_types:
			frappe.throw(_("{0} is a {1} contractor; this bill is for {2} contractors").format(
				self.contractor, ctype, " / ".join(self.allowed_types)))

	# --- rows -------------------------------------------------------------------------
	@frappe.whitelist()
	def fetch_slips(self):
		if not (self.contractor and self.from_date and self.to_date):
			frappe.throw(_("Select the Transport Contractor, From Date and To Date first"))
		period = ["between", [self.from_date, self.to_date]]
		slips = frappe.get_all(
			"Weighment Slip",
			filters={"docstatus": 1, "transport_contractor": self.contractor, "slip_date": period,
			         "tractor_bill": ["is", "not set"]},
			fields=["name", "slip_date"], order_by="slip_date, serial_no, name",
		)
		# diesel that does not ride on one of these slips: issued on its own, or against a slip of someone else's bill
		on_bill = {s.name for s in slips}
		diesel = [
			d for d in frappe.get_all(
				"Diesel Issue Entry",
				filters={"docstatus": 1, "transport_contractor": self.contractor, "issue_date": period,
				         "tractor_bill": ["is", "not set"]},
				fields=["name", "issue_date", "weighment_slip"], order_by="issue_date, name",
			)
			if d.weighment_slip not in on_bill
		]
		rows = [{"slip": s.name, "slip_date": s.slip_date} for s in slips]
		rows += [{"diesel_issue_entry": d.name, "slip_date": d.issue_date} for d in diesel]
		self.set("slips", [])
		for row in sorted(rows, key=lambda r: (getdate(r["slip_date"]), not r.get("slip"))):
			self.append("slips", row)
		# a fresh fetch recovers as much of the outstanding advance as the bill can bear; it can be lowered by hand
		self.advance_deduction = 0
		self.calculate()
		self.advance_deduction = flt(min(flt(self.outstanding_advance), max(flt(self.net_payable), 0)), 2)
		self.calculate()
		if not rows:
			frappe.msgprint(_("No unbilled weighment slips or diesel issues found for the selected period."))
		return len(rows)

	def set_row_values(self, row):
		if row.slip:
			self.set_slip_row(row)
		elif row.diesel_issue_entry:
			self.set_diesel_row(row)
		else:
			frappe.throw(_("Row {0}: a row needs a Weighment Slip or a Diesel Issue Entry").format(row.idx))

	def set_slip_row(self, row):
		slip = frappe.db.get_value(
			"Weighment Slip", row.slip,
			["slip_date", "vehicle_no", "village_name", "route", "distance", "delivery_type", "net_cane_weight"],
			as_dict=True,
		)
		if not slip:
			frappe.throw(_("Weighment Slip {0} does not exist").format(row.slip))
		rates = get_rate_master_rates(slip.slip_date, slip.delivery_type)
		if not rates:
			frappe.throw(_("No Cane Rate Master for {0} on {1}").format(slip.delivery_type, slip.slip_date))
		row.update({
			"slip_date": slip.slip_date, "vehicle": slip.vehicle_no, "village": slip.village_name,
			"route": slip.route, "distance": slip.distance, "delivery_type": slip.delivery_type,
			"net_weight": slip.net_cane_weight, "quantity": flt(flt(slip.net_cane_weight) / 1000, 3),
			"rate": rates["todani_rate"],
		})
		row.amount = flt(row.quantity * flt(row.rate), 2)
		# the one diesel issue made against this slip, unless another bill already recovered it
		diesel = frappe.db.get_value(
			"Diesel Issue Entry", {"weighment_slip": row.slip, "docstatus": 1},
			["name", "disel_qty", "tractor_bill", "transport_contractor", "issue_date"],
			as_dict=True,
		)
		if diesel and diesel.tractor_bill in (None, "", self.name) and diesel.transport_contractor == self.contractor:
			row.diesel_issue_entry, row.diesel_qty = diesel.name, flt(diesel.disel_qty)
			self.set_diesel_amount(row, diesel.issue_date)
		else:
			row.diesel_issue_entry, row.diesel_qty, row.diesel_rate, row.diesel_amount = None, 0, 0, 0

	def set_diesel_row(self, row):
		diesel = frappe.db.get_value(
			"Diesel Issue Entry", row.diesel_issue_entry, ["issue_date", "disel_qty", "tractor_number"], as_dict=True
		)
		if not diesel:
			frappe.throw(_("Diesel Issue Entry {0} does not exist").format(row.diesel_issue_entry))
		row.update({
			"slip_date": diesel.issue_date,
			"vehicle": frappe.db.get_value("Tractor Number", diesel.tractor_number, "tractor_number"),
			"village": None, "route": None, "distance": 0, "delivery_type": None,
			"net_weight": 0, "quantity": 0, "rate": 0, "amount": 0, "diesel_qty": flt(diesel.disel_qty),
		})
		self.set_diesel_amount(row, diesel.issue_date)

	def set_diesel_amount(self, row, issue_date):
		row.diesel_rate = get_diesel_rate(issue_date)
		row.diesel_amount = flt(flt(row.diesel_qty) * flt(row.diesel_rate), 2)

	# --- calculation ------------------------------------------------------------------
	def calculate(self):
		self.total_quantity = self.total_amount = self.total_diesel_qty = self.other_deduction = 0
		diesel_rates = set()
		for row in self.slips:
			self.set_row_values(row)
			self.total_quantity += flt(row.quantity)
			self.total_amount += flt(row.amount)
			self.total_diesel_qty += flt(row.diesel_qty)
			self.other_deduction += flt(row.diesel_amount)
			if flt(row.diesel_qty):
				diesel_rates.add(flt(row.diesel_rate))
		self.total_quantity = flt(self.total_quantity, 3)
		self.total_amount = flt(self.total_amount, 2)
		self.total_diesel_qty = flt(self.total_diesel_qty, 3)
		self.other_deduction = flt(self.other_deduction, 2)
		# one rate to show only when every litre on the bill was issued at the same rate
		self.diesel_rate = diesel_rates.pop() if len(diesel_rates) == 1 else 0
		self.farakt_amount = 0
		master_adv = frappe.db.get_value(
			"Contractor Master", self.contractor, ["total_advance_given", "advance_balance"], as_dict=True
		) or {}
		self.total_advance_given = flt(master_adv.get("total_advance_given"))
		# advance_balance = recovered so far; outstanding = what is still pending (clamped to 0)
		self.outstanding_advance = max(0.0, flt(self.total_advance_given) - flt(master_adv.get("advance_balance")))
		self.compute_net()
		self.outstanding_amount = flt(flt(self.net_payable) - flt(self.paid_amount), 2)

	def compute_net(self):
		if flt(self.advance_deduction) < 0:
			frappe.throw(_("Advance Deduction cannot be negative"))
		if flt(self.advance_deduction) > flt(self.outstanding_advance):
			frappe.throw(_("Advance Deduction {0} is more than the Outstanding Advance {1}").format(
				frappe.format(self.advance_deduction, {"fieldtype": "Currency"}),
				frappe.format(self.outstanding_advance, {"fieldtype": "Currency"})))
		self.deposit_deduction = flt(flt(self.total_amount) * DEPOSIT_PERCENT / 100, 2)
		if not 0 <= flt(self.commission_percent) <= 100:
			frappe.throw(_("Commission (%) must be between 0 and 100"))
		self.commission = flt(flt(self.total_amount) * flt(self.commission_percent) / 100, 2)
		self.total_deductions = flt(self.deposit_deduction + flt(self.other_deduction), 2)
		self.net_payable = flt(flt(self.total_amount) - self.total_deductions, 2)

	# --- lifecycle --------------------------------------------------------------------
	def before_submit(self):
		if not self.slips:
			frappe.throw(_("Nothing to bill. Use 'Fetch Weighment Slips'."))
		if flt(self.net_payable) < 0:
			frappe.throw(_("Total Recovery is more than the Total Amount, so the Final Payable Amount is negative"))
		# the bill is submitted by Pay; the advance it recovers must still be outstanding
		self.check_balances()
		seen = set()
		for row in self.slips:
			for doctype, name in (("Weighment Slip", row.slip), ("Diesel Issue Entry", row.diesel_issue_entry)):
				if not name:
					continue
				if (doctype, name) in seen:
					frappe.throw(_("Row {0}: {1} {2} is on this bill twice").format(row.idx, _(doctype), name))
				seen.add((doctype, name))
				doc = frappe.db.get_value(doctype, name, ["docstatus", "tractor_bill", "transport_contractor"], as_dict=True)
				if not doc or doc.docstatus != 1:
					frappe.throw(_("Row {0}: {1} {2} is not submitted").format(row.idx, _(doctype), name))
				if doc.tractor_bill and doc.tractor_bill != self.name:
					frappe.throw(_("Row {0}: {1} {2} is already billed in {3}").format(
						row.idx, _(doctype), name, doc.tractor_bill))
				if doc.transport_contractor != self.contractor:
					frappe.throw(_("Row {0}: {1} {2} belongs to another contractor").format(row.idx, _(doctype), name))
		self.validate_payment_details()

	def on_submit(self):
		self.set_billed(self.name)
		self.adjust_balances(1)   # advance_balance and deposit_balance accumulate (+)
		self.book_payment()

	def on_cancel(self):
		self.cancel_payment()
		self.adjust_balances(-1)  # reverse the accumulation
		self.set_billed(None)

	def set_billed(self, bill):
		"""Mark this bill's slips and diesel issues as billed here, or release the ones it holds."""
		for row in self.slips:
			for doctype, name in (("Weighment Slip", row.slip), ("Diesel Issue Entry", row.diesel_issue_entry)):
				if name and (bill or frappe.db.get_value(doctype, name, "tractor_bill") == self.name):
					frappe.db.set_value(doctype, name, "tractor_bill", bill, update_modified=False)


def get_diesel_rate(date):
	"""Diesel Rate (Per Litre) for diesel issued on `date`, from the Cane Rate Master covering that date.

	On or after the master's Diesel Effective Date it is the master's Diesel Rate; before it, the latest earlier
	rate the master kept. 0 when no master covers the date.
	"""
	if not date:
		return 0
	date = getdate(date)
	master = frappe.db.sql(
		"""select name, diesel_rate, ifnull(diesel_effective_date, effective_from) as since from `tabCane Rate Master`
		where disabled = 0 and effective_from <= %(d)s and (effective_to is null or effective_to >= %(d)s)
		order by effective_from desc, creation desc limit 1""",
		{"d": date}, as_dict=True,
	)
	if not master:
		return 0
	master = master[0]
	if date >= getdate(master.since):
		return flt(master.diesel_rate)
	earlier = frappe.get_all(
		"Cane Rate Diesel History", filters={"parent": master.name, "parenttype": "Cane Rate Master"},
		fields=["effective_from", "rate"], order_by="effective_from desc",
	)
	for row in earlier:
		if date >= getdate(row.effective_from):
			return flt(row.rate)
	# older than everything on record: the oldest rate known
	return flt(earlier[-1].rate) if earlier else flt(master.diesel_rate)
