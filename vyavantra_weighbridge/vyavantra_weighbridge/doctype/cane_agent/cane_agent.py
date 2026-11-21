# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CaneAgent(Document):
	def validate(self):
		# the name is the running number the database hands out (autoincrement)
		self.agent_no = self.name
