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
				frappe.throw(_("Row {0}: route {1} is added more than once").format(row.idx, row.route))
			seen.add(row.route)
