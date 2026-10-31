# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WeighbridgeAdvance(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("Amount must be greater than zero"))
		if self.party_type == "Agent" and self.entry_type == "Deposit":
			frappe.throw(_("Deposits are tracked for contractors only"))
		if not self.party:
			frappe.throw(_("Select the {0}").format(_(self.party_type)))

	@property
	def party(self):
		return self.contractor if self.party_type == "Contractor" else self.agent

	def balance_target(self):
		doctype = "Weighbridge Contractor" if self.party_type == "Contractor" else "Cane Agent"
		field = "advance_balance" if self.entry_type == "Advance" else "deposit_balance"
		return doctype, field

	def on_submit(self):
		self.adjust(flt(self.amount))

	def on_cancel(self):
		self.adjust(-flt(self.amount))

	def adjust(self, delta):
		doctype, field = self.balance_target()
		frappe.db.sql(f"select name from `tab{doctype}` where name = %s for update", self.party)
		bal = flt(frappe.db.get_value(doctype, self.party, field)) + delta
		if bal < 0:
			frappe.throw(_("Cancelling would make the {0} balance negative ({1})").format(_(self.entry_type), bal))
		frappe.db.set_value(doctype, self.party, field, bal)
