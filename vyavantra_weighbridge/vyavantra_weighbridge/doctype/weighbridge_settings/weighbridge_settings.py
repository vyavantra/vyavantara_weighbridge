# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from vyavantra_weighbridge.utils import LOGO_LIMITS


class WeighbridgeSettings(Document):
	def validate(self):
		for key, (low, high, _default) in LOGO_LIMITS.items():
			value = cint(self.get(key))
			if value and not low <= value <= high:
				frappe.throw(_("{0} must be between {1} and {2} px (or 0 for automatic)").format(
					_(self.meta.get_label(key)), low, high))

	def on_update(self):
		# the logo size travels in the boot data, which is cached per user
		frappe.cache.delete_key("bootinfo")
