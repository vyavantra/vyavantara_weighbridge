# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowtime

from vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip import get_village_route_rows


class SlipBoyEntry(Document):
	def validate(self):
		if not self.farmer and not (self.new_farmer_name or "").strip():
			frappe.throw(_("Select a farmer or enter New Farmer Name"))
		if self.farmer and self.new_farmer_name:
			frappe.throw(_("Choose an existing farmer or create a new farmer, not both"))
		if self.trailer_2 and (not self.trailer or self.trailer_2 == self.trailer):
			frappe.throw(_("Trailer 2 must differ from Trailer 1"))

		village = frappe.db.get_value("Cane Supplier", self.farmer, "village") if self.farmer else self.village
		if not self.farmer and not village:
			frappe.throw(_("Select a village for the new farmer"))
		routes = get_village_route_rows(village)
		if self.route and self.route not in routes:
			frappe.throw(_("Route {0} is not defined for village {1}").format(self.route, village or ""))
		if routes and not self.route:
			frappe.throw(_("Please select a route for village {0}").format(village))

	def on_submit(self):
		if self.new_farmer_name:
			from vyavantra_weighbridge.vyavantra_weighbridge.doctype.cane_supplier.cane_supplier import ensure_bank

			bank = ensure_bank(self.bank) if self.bank else None
			farmer = frappe.get_doc({
				"doctype": "Cane Supplier",
				"farmer_name": self.new_farmer_name.strip(),
				"phone": self.phone,
				"village": self.village,
				"address": self.address,
				"bank": bank,
				"bank_account_no": self.bank_account_no,
				"ifsc_code": self.ifsc_code,
				"aadhaar_number": self.aadhaar_number,
				"bank_passbook_image": self.bank_passbook_image,
				"aadhaar_card_image": self.aadhaar_card_image,
			}).insert(ignore_permissions=True)
			self.db_set("farmer", farmer.name, update_modified=False)

		slip = frappe.get_doc({
			"doctype": "Weighment Slip",
			"slip_date": getdate(self.slip_date),
			"slip_time": nowtime(),
			"field_slip_number": self.field_slip_number,
			"farmer": self.farmer,
			"route": self.route,
			"delivery_type": self.delivery_type,
			"cane_type": self.cane_type,
			"variety": self.variety,
			"vehicle": self.vehicle,
			"trailer": self.trailer,
			"trolley_type": self.trolley_type,
			"trailer_2": self.trailer_2,
			"trolley_type_2": self.trolley_type_2,
			"transport_contractor": self.transport_contractor,
			"cutting_contractor": self.cutting_contractor,
			"agent": self.agent,
			"remarks": self.remarks,
		}).insert(ignore_permissions=True)
		self.db_set("weighment_slip", slip.name, update_modified=False)

	def on_cancel(self):
		if self.weighment_slip and frappe.db.exists("Weighment Slip", self.weighment_slip):
			slip = frappe.get_doc("Weighment Slip", self.weighment_slip)
			if slip.docstatus != 0:
				frappe.throw(_("Cancel Weighment Slip {0} before cancelling this entry").format(slip.name))
			# Clear the Link first: Frappe refuses to delete a draft still referenced by this entry.
			self.db_set("weighment_slip", None, update_modified=False)
			frappe.delete_doc("Weighment Slip", slip.name, ignore_permissions=True)
