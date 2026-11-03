# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.model.naming import make_autoname


class CaneAgent(Document):
	def autoname(self):
		self.name = make_autoname("Agent-.###")
		self.agent_no = self.name
