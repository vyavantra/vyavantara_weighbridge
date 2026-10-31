# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

from frappe.utils import flt

from vyavantra_weighbridge.billing import SlipBill


class FarmerBill(SlipBill):
	party_field = "farmer"
	slip_party_field = "farmer"
	flag_field = "farmer_bill"
	slip_rate_field = "cane_rate"

	def compute_net(self):
		self.total_deductions = flt(flt(self.cash_discount) + flt(self.wade) + flt(self.other_deduction), 2)
		self.net_payable = flt(flt(self.total_amount) - self.total_deductions, 2)
