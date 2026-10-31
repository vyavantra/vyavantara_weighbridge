# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

from vyavantra_weighbridge.billing import SlipBill


class AgentBill(SlipBill):
	party_field = "agent"
	slip_party_field = "agent"
	flag_field = "agent_bill"
	slip_rate_field = "commission_rate"
	party_doctype = "Cane Agent"
	balance_deductions = (("advance_deduction", "advance_balance"),)

	def validate_party(self):
		if not flt(self.commission_rate) and self.agent:
			self.commission_rate = flt(frappe.db.get_value("Cane Agent", self.agent, "commission_rate"))

	def set_row_rate(self, row):
		row.rate = flt(self.commission_rate)

	def slip_rate(self, slip):
		return flt(self.commission_rate)

	def compute_net(self):
		self.total_deductions = flt(flt(self.advance_deduction) + flt(self.other_deduction), 2)
		self.net_payable = flt(flt(self.total_amount) - self.total_deductions, 2)
