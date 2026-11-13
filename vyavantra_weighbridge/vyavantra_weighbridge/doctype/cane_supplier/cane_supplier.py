# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form


class CaneSupplier(Document):
	def validate(self):
		# the name is the running number the database hands out (autoincrement)
		self.cane_supplier_no = self.name
		self.fill_place_from_village()
		self.check_duplicate_name()
		self.validate_aadhaar()

	def fill_place_from_village(self):
		"""Taluka and district belong to the village, so they are never typed twice.

		It also keeps the duplicate check honest: two members of one village always carry the same
		taluka and district, instead of one record having them and another leaving them empty.
		"""
		if not self.village:
			return

		place = frappe.db.get_value("Village Master", self.village, ["taluka", "district"], as_dict=True)
		if not place:
			return

		self.taluka = place.taluka
		self.district = place.district

	def validate_aadhaar(self):
		"""Aadhaar is optional, but a supplied value must be exactly twelve digits."""
		value = (self.aadhaar_number or "").strip()
		if value and (len(value) != 12 or not value.isascii() or not value.isdigit()):
			frappe.throw(_("Aadhaar Number must contain exactly 12 digits"))
		self.aadhaar_number = value

	def check_duplicate_name(self):
		"""Two members of the same village cannot carry the same name.

		Relatives in one village often share a name; the office tells them apart by adding something in
		brackets, e.g. "Ramesh Patil (Bapu)". The same name is allowed in a different village, so the
		check is on name + village + taluka + district together.
		"""
		if not self.farmer_name:
			return

		# ifnull(), because a blank place is stored as NULL on one record and "" on another, and SQL
		# compares NULL to nothing at all
		existing = frappe.db.sql(
			"""select name from `tabCane Supplier`
			where farmer_name = %(farmer_name)s
				and ifnull(village, '') = %(village)s
				and ifnull(taluka, '') = %(taluka)s
				and ifnull(district, '') = %(district)s
				and name != %(name)s
			limit 1""",
			{
				"farmer_name": self.farmer_name,
				"village": self.village or "",
				"taluka": self.taluka or "",
				"district": self.district or "",
				"name": self.name or "",
			},
		)
		if not existing:
			return
		existing = existing[0][0]

		where = self.village or self.taluka or self.district or _("the same place")
		frappe.throw(
			_("{0} already exists in {1} as {2}.").format(
				frappe.bold(self.farmer_name), frappe.bold(where), get_link_to_form("Cane Supplier", existing)
			)
			+ "<br><br>"
			+ _("Add something in brackets to tell them apart, for example {0}.").format(
				frappe.bold(f"{self.farmer_name} (\u0906\u092a\u094d\u092a\u093e)")
			),
			title=_("Duplicate Member"),
		)


@frappe.whitelist()
def bank_choices():
	"""Bank names for Slip Boy's farmer dialog, without granting the role access to all Bank records."""
	frappe.has_permission("Cane Supplier", "create", throw=True)
	return frappe.get_all("Bank", fields=["name"], order_by="name", limit_page_length=500)


@frappe.whitelist()
def ensure_bank(bank_name):
	"""Add a bank name from the farmer dialog without granting general Bank permissions."""
	frappe.has_permission("Cane Supplier", "create", throw=True)
	bank_name = (bank_name or "").strip()
	if not bank_name:
		frappe.throw(_("Enter a bank name"))
	if frappe.db.exists("Bank", bank_name):
		return bank_name
	return frappe.get_doc({"doctype": "Bank", "bank_name": bank_name}).insert(ignore_permissions=True).name
