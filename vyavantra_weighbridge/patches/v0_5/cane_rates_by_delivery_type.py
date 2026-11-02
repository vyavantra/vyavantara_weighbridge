"""Cane Rate Master now holds one row per Delivery Type (cane / todani / farak rate).

Runs after model sync: the old flat columns of `tabCane Rate Master` are still there (Frappe does not drop
columns). Every master that has no rate rows yet gets one row per Delivery Type that had a cane rate;
the old todani and farak rate are copied into every row.
"""

import frappe
from frappe.utils import flt

# "Farmer Cane" is no longer a Delivery Type of the slip, so its old flat rate is not carried over
OLD_CANE_COLUMN = {
	"Farm Delivery": "farm_delivery_rate",
	"Gate Cane": "gate_cane_rate",
	"Harvesting Machine": "harvesting_machine_rate",
}


def execute():
	if not (frappe.db.has_column("Cane Rate Master", "farm_delivery_rate") and frappe.db.table_exists("Delivery Type")):
		return
	cols = [c for c in ("todani_rate", "farak_rate") if frappe.db.has_column("Cane Rate Master", c)]
	for m in frappe.db.sql(
		"select name, {0} from `tabCane Rate Master`".format(", ".join(list(OLD_CANE_COLUMN.values()) + cols)),
		as_dict=True,
	):
		if frappe.db.exists("Cane Rate Delivery Type", {"parent": m.name, "parenttype": "Cane Rate Master"}):
			continue
		idx = 0
		for delivery_type, column in OLD_CANE_COLUMN.items():
			if flt(m.get(column)) <= 0:
				continue
			idx += 1
			if not frappe.db.exists("Delivery Type", delivery_type):
				frappe.get_doc({"doctype": "Delivery Type", "delivery_type_name": delivery_type}).insert(ignore_permissions=True)
			frappe.get_doc({
				"doctype": "Cane Rate Delivery Type",
				"parent": m.name, "parenttype": "Cane Rate Master", "parentfield": "rates", "idx": idx,
				"delivery_type": delivery_type, "cane_rate": flt(m.get(column)),
				"todani_rate": flt(m.get("todani_rate")), "farak_rate": flt(m.get("farak_rate")),
			}).db_insert()
