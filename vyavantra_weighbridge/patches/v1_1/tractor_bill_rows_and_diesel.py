"""Tractor Contractor Bill rows move to their own table, and diesel issues learn whose bill recovers them.

Rows keep the quantity, rate and amount they were booked with; a draft bill recalculates on its next save.
"""

import frappe

from vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip import get_tractor_contractor


def execute():
	for doctype in ("tractor_bill_slip", "tractor_contractor_bill", "diesel_issue_entry", "cane_rate_master"):
		frappe.reload_doc("vyavantra_weighbridge", "doctype", doctype)

	old_rows = frappe.get_all(
		"Weighbridge Bill Slip", filters={"parenttype": "Tractor Contractor Bill"},
		fields=["parent", "idx", "slip", "slip_date", "vehicle", "village", "net_weight", "quantity", "rate", "amount"],
		order_by="parent, idx",
	)
	for row in old_rows:
		slip = frappe.db.get_value(
			"Weighment Slip", row.slip, ["route", "distance", "delivery_type", "village_name"], as_dict=True
		) if row.slip else None
		frappe.get_doc({
			"doctype": "Tractor Bill Slip", "parent": row.parent, "parenttype": "Tractor Contractor Bill",
			"parentfield": "slips", "idx": row.idx, "slip": row.slip, "slip_date": row.slip_date,
			"vehicle": row.vehicle, "village": (slip.village_name if slip else None) or row.village,
			"route": slip.route if slip else None, "distance": slip.distance if slip else 0,
			"delivery_type": slip.delivery_type if slip else None,
			"net_weight": row.net_weight, "quantity": row.quantity, "rate": row.rate, "amount": row.amount,
		}).db_insert()
	frappe.db.delete("Weighbridge Bill Slip", {"parenttype": "Tractor Contractor Bill"})

	# masters made before the Diesel Rate existed take its default
	frappe.db.sql("update `tabCane Rate Master` set diesel_rate = 100 where ifnull(diesel_rate, 0) = 0")

	# diesel issued before this link existed is recovered from the contractor who owns the tractor
	for entry in frappe.get_all(
		"Diesel Issue Entry", filters={"transport_contractor": ["is", "not set"], "tractor_number": ["is", "set"]},
		fields=["name", "tractor_number"],
	):
		contractor = get_tractor_contractor(entry.tractor_number)
		if contractor:
			frappe.db.set_value("Diesel Issue Entry", entry.name, "transport_contractor", contractor, update_modified=False)
