# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowtime


class GeneralWeighmentSlip(Document):
	"""Weighment of anything that is not cane: product, vehicle, party and the two weights."""

	def before_insert(self):
		self.serial_no = (
			cint(
				frappe.db.sql(
					"select max(serial_no) from `tabGeneral Weighment Slip` where slip_date = %s", self.slip_date
				)[0][0]
			)
			+ 1
		)

	def validate(self):
		if not self.slip_time:
			self.slip_time = nowtime()
		self.calculate_weights()
		if self.amended_from and not self.remarks:
			frappe.throw(_("Please enter the reason for the re-weighing / correction in Remarks"))

	def calculate_weights(self):
		"""Net Weight = Loaded Vehicle Weight - Empty Vehicle Weight, recalculated here whatever the client sent."""
		loaded, empty = flt(self.loaded_weight), flt(self.empty_weight)
		if loaded < 0 or empty < 0:
			frappe.throw(_("Weights cannot be negative"))
		if loaded and empty and loaded <= empty:
			frappe.throw(_("Loaded Vehicle Weight must be greater than Empty Vehicle Weight"))
		# with the empty weight still 0 the net simply follows the loaded weight
		self.net_weight = flt(loaded - empty, 2) if loaded else 0

	def before_submit(self):
		if not flt(self.empty_weight) or not flt(self.loaded_weight):
			frappe.throw(_("Both Empty and Loaded Vehicle Weights must be taken before submitting"))
		if flt(self.net_weight) <= 0:
			frappe.throw(_("Net Weight must be greater than zero"))
