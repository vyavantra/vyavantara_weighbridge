# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class VillageMaster(Document):
	def autoname(self):
		self.name = make_autoname("Village-.###")
		self.village_no = self.name

	def validate(self):
		seen = set()
		for row in self.routes:
			if row.route in seen:
				frappe.throw(_("Row #{0}: Route {1} is added twice for this village").format(row.idx, row.route))
			seen.add(row.route)
			if row.distance_km is None or row.distance_km <= 0:
				frappe.throw(_("Row #{0}: Distance must be greater than zero").format(row.idx))
			if row.transport_rate is None or row.transport_rate < 0:
				frappe.throw(_("Row #{0}: Rate cannot be negative").format(row.idx))
