# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.model.naming import make_autoname


class ContractorMaster(Document):
	def autoname(self):
		self.name = make_autoname("Contractor-.###")
		self.contractor_no = self.name
