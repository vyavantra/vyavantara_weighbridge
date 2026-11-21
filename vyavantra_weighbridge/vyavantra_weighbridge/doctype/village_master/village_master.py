# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class VillageMaster(Document):
	def validate(self):
		# the name is the running number the database hands out (autoincrement)
		self.village_no = self.name
		seen = set()
		for row in self.routes:
			if row.route in seen:
				frappe.throw(_("Row #{0}: Route {1} is added twice for this village").format(row.idx, row.route))
			seen.add(row.route)
			if row.distance_km is not None and row.distance_km < 0:
				frappe.throw(_("Row #{0}: Distance cannot be negative").format(row.idx))
			if row.transport_rate is not None and row.transport_rate < 0:
				frappe.throw(_("Row #{0}: Rate cannot be negative").format(row.idx))
