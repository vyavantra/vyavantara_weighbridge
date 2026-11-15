"""Move only Farmer Bill rows from shared Weighbridge Bill Slip to Farmer Bill Slip.

Other bill types continue using Weighbridge Bill Slip. Keep submitted bills' booked amount/rate and
payment summary as-is; draft bills recalculate from the effective Cane Rate Master on next save.
"""

import frappe


WEIGHT_FIELDS = (
	"slip_date", "delivery_type", "cane_weight", "mat_weight", "net_after_binding",
	"other_deduction_percent", "other_deduction", "net_cane_weight", "vehicle_no", "village",
)


def execute():
	for bill in frappe.get_all("Farmer Bill", fields=["name", "docstatus"]):
		rows = frappe.get_all(
			"Weighbridge Bill Slip", filters={"parent": bill.name, "parenttype": "Farmer Bill"},
			fields=["name", "idx", "slip", "slip_date", "vehicle", "village", "net_weight", "quantity", "rate", "amount"],
			order_by="idx",
		)
		if not rows:
			continue
		for row in rows:
			slip = frappe.db.get_value("Weighment Slip", row.slip, WEIGHT_FIELDS, as_dict=True) if row.slip else None
			frappe.get_doc({
				"doctype": "Farmer Bill Slip", "parent": bill.name, "parenttype": "Farmer Bill",
				"parentfield": "slips", "idx": row.idx, "slip": row.slip,
				"slip_date": (slip.slip_date if slip else row.slip_date),
				"delivery_type": slip.delivery_type if slip else None,
				"vehicle": (slip.vehicle_no if slip else row.vehicle),
				"village": (slip.village if slip else row.village),
				"cane_weight": slip.cane_weight if slip else 0,
				"mat_weight": slip.mat_weight if slip else 0,
				"net_after_binding": slip.net_after_binding if slip else 0,
				"other_deduction_percent": slip.other_deduction_percent if slip else 0,
				"other_deduction": slip.other_deduction if slip else 0,
				"net_weight": (slip.net_cane_weight if slip else row.net_weight),
				"quantity": row.quantity, "rate": row.rate, "amount": row.amount,
			}).db_insert()
		frappe.db.delete("Weighbridge Bill Slip", {"parent": bill.name, "parenttype": "Farmer Bill"})
