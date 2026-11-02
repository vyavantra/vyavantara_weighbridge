# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class ContractorMaster(Document):
	def autoname(self):
		self.name = make_autoname("Contractor-.###")
		self.contractor_no = self.name

	def validate(self):
		seen = set()
		for row in self.tractors:
			if row.tractor_number in seen:
				frappe.throw(_("Row {0}: Tractor Number {1} is entered twice").format(row.idx, row.tractor_number))
			seen.add(row.tractor_number)
