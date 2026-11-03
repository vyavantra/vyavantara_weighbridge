# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import re

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
			row.tractor_no = re.sub(r"\s+", "", row.tractor_no or "").upper()
			if row.tractor_no in seen:
				frappe.throw(_("Row {0}: tractor {1} is added more than once").format(row.idx, row.tractor_no))
			seen.add(row.tractor_no)
			owner = frappe.db.get_value("Weighbridge Vehicle", row.tractor_no, "contractor")
			if owner and owner != self.name:
				frappe.throw(_("Row {0}: tractor {1} already belongs to contractor {2}").format(row.idx, row.tractor_no, owner))

	def on_update(self):
		"""Tractors entered here become Weighbridge Vehicles, so they can be picked on the weighment slip."""
		for row in self.tractors:
			if frappe.db.exists("Weighbridge Vehicle", row.tractor_no):
				frappe.db.set_value("Weighbridge Vehicle", row.tractor_no,
									{"contractor": self.name, "trolley_type": row.trolley_type or None})
			else:
				frappe.get_doc({"doctype": "Weighbridge Vehicle", "vehicle_no": row.tractor_no,
								"trolley_type": row.trolley_type or None, "contractor": self.name}).insert(ignore_permissions=True)
