# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.model.naming import make_autoname


class CaneSupplier(Document):
	def autoname(self):
		self.name = make_autoname("Cane-Supplier-.###")
		self.cane_supplier_no = self.name
