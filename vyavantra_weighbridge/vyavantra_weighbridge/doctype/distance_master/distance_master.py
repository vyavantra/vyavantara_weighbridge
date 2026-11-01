# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document


class DistanceMaster(Document):
	def autoname(self):
		self.distance_label = f"{flt(self.distance_km):g} Km"
		self.name = self.distance_label

	def validate(self):
		if flt(self.distance_km) <= 0:
			frappe.throw(_("Distance must be greater than zero"))
