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
		if not 0 <= flt(self.binding_deduction_percent) <= 100:
			frappe.throw(_("Binding Deduction % must be between 0 and 100"))
		self.keep_diesel_rate_history()
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

	def keep_diesel_rate_history(self):
		"""A changed Diesel Rate takes effect from its date; the rate it replaces stays on record for earlier diesel."""
		if flt(self.diesel_rate) < 0:
			frappe.throw(_("Diesel Rate cannot be negative"))
		if not self.diesel_effective_date:
			self.diesel_effective_date = self.effective_from
		before = self.get_doc_before_save()
		if not before or not before.diesel_effective_date:
			return
		rate_changed = flt(before.diesel_rate) != flt(self.diesel_rate)
		date_changed = getdate(before.diesel_effective_date) != getdate(self.diesel_effective_date)
		if not rate_changed:
			return
		if not date_changed:
			frappe.throw(_("Set the Diesel Effective Date from which the new Diesel Rate applies"))
		if getdate(self.diesel_effective_date) < getdate(before.diesel_effective_date):
			frappe.throw(_("The new Diesel Effective Date cannot be before the current one ({0})").format(
				frappe.format(before.diesel_effective_date, {"fieldtype": "Date"})))
		self.append("diesel_rate_history", {"effective_from": before.diesel_effective_date, "rate": before.diesel_rate})
