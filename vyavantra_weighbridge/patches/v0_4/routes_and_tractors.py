import frappe

from vyavantra_weighbridge.setup import after_migrate_setup


def execute():
	# village distance/rate moved from the village form into its Routes table
	if frappe.db.has_column("Village Master", "distance_master"):
		for v in frappe.db.sql("select name, village_name, distance_master from `tabVillage Master`", as_dict=True):
			if not v.distance_master or frappe.db.exists("Village Route", {"parent": v.name}):
				continue
			route = f"{v.village_name} Route"
			if not frappe.db.exists("Route Master", route):
				frappe.get_doc({"doctype": "Route Master", "route_name": route}).insert(ignore_permissions=True)
			doc = frappe.get_doc("Village Master", v.name)
			doc.append("routes", {"route": route, "distance_master": v.distance_master})
			doc.save(ignore_permissions=True)

	# contractor tractor numbers: former single vehicle_no field plus vehicles already linked to the contractor
	for c in frappe.get_all("Contractor Master", pluck="name"):
		doc = frappe.get_doc("Contractor Master", c)
		have = {r.tractor_no for r in doc.tractors}
		old = frappe.db.get_value("Contractor Master", c, "vehicle_no") if frappe.db.has_column("Contractor Master", "vehicle_no") else None
		vehicles = frappe.get_all("Weighbridge Vehicle", filters={"contractor": c}, fields=["vehicle_no", "trolley_type"])
		for no, tt in [(old, None)] + [(v.vehicle_no, v.trolley_type) for v in vehicles]:
			if no and no not in have:
				doc.append("tractors", {"tractor_no": no, "trolley_type": tt})
				have.add(no)
		if len(doc.tractors) != len(frappe.get_all("Contractor Tractor", filters={"parent": c})):
			doc.save(ignore_permissions=True)

	after_migrate_setup()
