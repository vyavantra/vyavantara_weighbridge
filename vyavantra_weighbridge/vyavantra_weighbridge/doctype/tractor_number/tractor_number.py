# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TractorNumber(Document):
	def validate(self):
		self.normalise_number()
		self.check_duplicate()

	def normalise_number(self):
		"""A vehicle number is written in capitals: mh11ab1234 typed in a hurry is MH11AB1234.

		The spacing people use varies (MH 11 AB 1234, MH-11-AB-1234), so the inner spaces and dashes are
		kept as typed; only the letters change case.
		"""
		if self.tractor_number:
			self.tractor_number = self.tractor_number.strip().upper()

	def check_duplicate(self):
		"""The same vehicle must not be on two records, or a slip would pick the wrong owner."""
		if not self.tractor_number:
			return

		existing = frappe.db.get_value(
			"Tractor Number",
			{"tractor_number": self.tractor_number, "name": ("!=", self.name)},
			"name",
		)
		if existing:
			frappe.throw(
				_("Vehicle {0} already exists as {1}").format(
					frappe.bold(self.tractor_number), frappe.utils.get_link_to_form("Tractor Number", existing)
				),
				title=_("Duplicate Vehicle"),
			)
