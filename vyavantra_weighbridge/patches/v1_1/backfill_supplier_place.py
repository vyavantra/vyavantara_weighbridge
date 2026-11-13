"""Taluka, District and State on members that were entered before the village filled them in.

The village already knows its taluka and district, so the pair is copied down. Everyone here is in
Maharashtra, which is the default on the field; members entered earlier simply have it empty.
"""

import frappe


def execute():
	if not frappe.db.has_column("Cane Supplier", "state"):
		return

	villages = {
		v.name: v for v in frappe.get_all("Village Master", fields=["name", "taluka", "district"])
	}

	for member in frappe.get_all(
		"Cane Supplier", fields=["name", "village", "taluka", "district", "state"]
	):
		update = {}

		place = villages.get(member.village)
		if place:
			if not member.taluka and place.taluka:
				update["taluka"] = place.taluka
			if not member.district and place.district:
				update["district"] = place.district

		if not member.state:
			update["state"] = "Maharashtra"

		if update:
			frappe.db.set_value("Cane Supplier", member.name, update, update_modified=False)

	frappe.db.commit()
