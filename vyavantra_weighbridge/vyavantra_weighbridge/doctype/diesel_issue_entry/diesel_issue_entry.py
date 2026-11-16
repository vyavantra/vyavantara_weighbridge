# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip import get_tractor_contractor


class DieselIssueEntry(Document):
	def validate(self):
		if flt(self.disel_qty) <= 0:
			frappe.throw(_("Diesel Qty must be greater than zero"))
		if self.weighment_slip:
			self.set_from_weighment_slip()
		elif not self.transport_contractor:
			# diesel issued on its own is recovered from the contractor who owns the tractor
			self.transport_contractor = get_tractor_contractor(self.tractor_number)

	def set_from_weighment_slip(self):
		slip = frappe.db.get_value(
			"Weighment Slip", self.weighment_slip, ["docstatus", "transport_contractor", "vehicle"], as_dict=True
		)
		if not slip or slip.docstatus != 1:
			frappe.throw(_("Weighment Slip {0} is not submitted").format(self.weighment_slip))
		other = frappe.db.get_value(
			"Diesel Issue Entry",
			{"weighment_slip": self.weighment_slip, "docstatus": ["<", 2], "name": ["!=", self.name or ""]},
		)
		if other:
			frappe.throw(_("Diesel Issue Entry {0} already exists for Weighment Slip {1}").format(other, self.weighment_slip))
		# what the slip records is fixed; a slip without a contractor or tractor leaves them as entered here
		self.transport_contractor = slip.transport_contractor or self.transport_contractor
		self.tractor_number = slip.vehicle or self.tractor_number
		if not self.transport_contractor:
			frappe.throw(_("Choose the Transport Contractor the diesel is issued to"))

	def on_cancel(self):
		if self.tractor_bill:
			frappe.throw(_("This diesel is billed in {0}. Cancel that bill first.").format(self.tractor_bill))


def get_or_create_receiver(contractor):
	"""The Diesel Receiver of a transport contractor: the receiver carrying the contractor's name."""
	name = (frappe.db.get_value("Contractor Master", contractor, "contractor_name") or "").strip()
	if not name:
		return None
	receiver = frappe.db.get_value("Diesel Receiver", {"disel_receiver_name": name})
	if not receiver:
		receiver = frappe.get_doc({"doctype": "Diesel Receiver", "disel_receiver_name": name}).insert(
			ignore_permissions=True
		).name
	return receiver


@frappe.whitelist()
def get_for_weighment_slip(weighment_slip):
	"""The Diesel Issue Entry made against a weighment slip, if any."""
	frappe.has_permission("Weighment Slip", "read", weighment_slip, throw=True)
	return frappe.db.get_value(
		"Diesel Issue Entry", {"weighment_slip": weighment_slip, "docstatus": ["<", 2]}, ["name", "disel_qty", "docstatus"],
		as_dict=True,
	)


@frappe.whitelist()
def create_from_weighment_slip(weighment_slip, petrol_pump, diesel_qty, transport_contractor=None, tractor_number=None):
	"""Issue diesel against a submitted weighment slip: date, receiver and tractor come from the slip.
	`transport_contractor` and `tractor_number` are used only where the slip itself has none."""
	slip = frappe.get_doc("Weighment Slip", weighment_slip)
	slip.check_permission("read")
	if slip.docstatus != 1:
		frappe.throw(_("Submit the Weighment Slip first"))
	contractor = slip.transport_contractor or transport_contractor
	if not contractor:
		frappe.throw(_("Choose the Transport Contractor the diesel is issued to"))
	entry = frappe.get_doc({
		"doctype": "Diesel Issue Entry",
		"issue_date": slip.slip_date,
		"disel_receiver_name": get_or_create_receiver(contractor),
		"tractor_number": slip.vehicle or tractor_number,
		"petrol_pump_name": petrol_pump,
		"disel_qty": flt(diesel_qty),
		"weighment_slip": slip.name,
		"transport_contractor": contractor,
	})
	entry.insert()
	entry.submit()
	return entry.name
