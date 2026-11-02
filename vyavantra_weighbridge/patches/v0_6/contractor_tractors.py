"""Contractor Master keeps its tractors in a child table (Tractor Number master); Weighbridge Vehicle is gone.

Runs before model sync, while the old columns / tables are still present:
- a contractor that had a single `vehicle_no` gets one tractor row for it (the Tractor Number record is created if missing)
- every Weighbridge Vehicle with a Linked Contractor becomes a tractor row of that contractor
- Contractor Type "Transport" becomes "Tractor" and "Todani" becomes "Cutting Contractor" (the only two types left)
- Weighment Slip.vehicle used to hold a Weighbridge Vehicle name, it now holds a Tractor Number name
"""

import frappe

TYPE_MAP = {"Transport": "Tractor", "Todani": "Cutting Contractor"}


def tractor_name(number):
	number = (number or "").strip()
	if not number:
		return None
	name = frappe.db.get_value("Tractor Number", {"tractor_number": number}, "name")
	if not name:
		doc = frappe.get_doc({"doctype": "Tractor Number", "tractor_number": number})
		doc.insert(ignore_permissions=True)
		name = doc.name
	return name


def add_tractor(contractor, tractor):
	if not tractor or frappe.db.exists("Contractor Tractor", {"parent": contractor, "parenttype": "Contractor Master", "tractor_number": tractor}):
		return
	idx = frappe.db.count("Contractor Tractor", {"parent": contractor, "parenttype": "Contractor Master"}) + 1
	frappe.get_doc({
		"doctype": "Contractor Tractor", "parent": contractor, "parenttype": "Contractor Master",
		"parentfield": "tractors", "idx": idx, "tractor_number": tractor,
	}).db_insert()


def execute():
	if not (frappe.db.table_exists("Contractor Master") and frappe.db.table_exists("Tractor Number")):
		return
	if not frappe.db.table_exists("Contractor Tractor"):
		frappe.reload_doc("vyavantra_weighbridge", "doctype", "contractor_tractor")

	for old, new in TYPE_MAP.items():
		frappe.db.sql("update `tabContractor Master` set contractor_type = %s where contractor_type = %s", (new, old))

	if frappe.db.has_column("Contractor Master", "vehicle_no"):
		for c in frappe.db.sql("select name, vehicle_no from `tabContractor Master` where ifnull(vehicle_no, '') != ''", as_dict=True):
			add_tractor(c.name, tractor_name(c.vehicle_no))

	if frappe.db.table_exists("Weighbridge Vehicle"):
		vehicles = frappe.db.sql("select name, contractor from `tabWeighbridge Vehicle`", as_dict=True)
		by_vehicle = {}
		for v in vehicles:
			tractor = tractor_name(v.name)
			by_vehicle[v.name] = tractor
			if v.contractor:
				add_tractor(v.contractor, tractor)
		if frappe.db.table_exists("Weighment Slip"):
			for vehicle, tractor in by_vehicle.items():
				frappe.db.sql("update `tabWeighment Slip` set vehicle = %s where vehicle = %s", (tractor, vehicle))
	frappe.db.commit()
