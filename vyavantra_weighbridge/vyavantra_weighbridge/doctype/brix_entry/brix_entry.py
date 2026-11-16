# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_time

TIME_12 = "%I:%M %p"
# what an operator may type: 2:35 PM, 02:35pm, 2.35 PM, 14:35
TYPED_FORMATS = ("%I:%M %p", "%I:%M%p", "%I.%M %p", "%I.%M%p", "%I %p", "%I%p", "%H:%M", "%H:%M:%S")


def parse_time_12(text):
	text = " ".join((text or "").upper().split())
	for fmt in TYPED_FORMATS:
		try:
			return datetime.strptime(text, fmt).time()
		except ValueError:
			pass
	return None


class BrixEntry(Document):
	def validate(self):
		# Time is stored on the 24 hour clock in entry_time; the form shows and takes it as entry_time_12
		typed = self.has_value_changed("entry_time_12") and not self.has_value_changed("entry_time")
		if typed and self.entry_time_12:
			time = parse_time_12(self.entry_time_12)
			if not time:
				frappe.throw(_("Time {0} is not a clock time. Enter it like 02:35 PM.").format(self.entry_time_12))
			self.entry_time = time.strftime("%H:%M:%S")
		self.entry_time_12 = get_time(self.entry_time).strftime(TIME_12) if self.entry_time else None
