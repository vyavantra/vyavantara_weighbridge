# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class CaneRateMaster(Document):
	def validate(self):
		if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
			frappe.throw(_("Effective To cannot be before Effective From"))
		if not self.rates:
			frappe.throw(_("Add the rate of at least one Delivery Type"))
		seen = set()
		for row in self.rates:
			if row.delivery_type in seen:
				frappe.throw(_("Row {0}: Delivery Type {1} is entered twice").format(row.idx, row.delivery_type))
			seen.add(row.delivery_type)
			if flt(row.cane_rate) <= 0:
				frappe.throw(_("Row {0}: Cane Rate must be greater than zero").format(row.idx))
			if flt(row.todani_rate) < 0 or flt(row.farak_rate) < 0:
				frappe.throw(_("Row {0}: rates cannot be negative").format(row.idx))
