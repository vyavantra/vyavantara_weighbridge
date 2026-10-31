# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from vyavantra_weighbridge.billing import SlipBill


class TractorContractorBill(SlipBill):
	party_field = "contractor"
	slip_party_field = "transport_contractor"
	flag_field = "tractor_bill"
	slip_rate_field = "transport_rate"
	party_doctype = "Weighbridge Contractor"
	balance_deductions = (("advance_deduction", "advance_balance"), ("deposit_deduction", "deposit_balance"))
	allowed_types = ("Tractor", "Transport")

	def validate_party(self):
		ctype = frappe.db.get_value("Weighbridge Contractor", self.contractor, "contractor_type")
		if ctype not in self.allowed_types:
			frappe.throw(_("{0} is a {1} contractor; this bill is for {2} contractors").format(
				self.contractor, ctype, " / ".join(self.allowed_types)))

	def compute_net(self):
		self.total_deductions = flt(
			flt(self.farakt_amount) + flt(self.advance_deduction) + flt(self.deposit_deduction)
			+ flt(self.other_deduction), 2)
		self.net_payable = flt(flt(self.total_amount) - self.total_deductions, 2)
