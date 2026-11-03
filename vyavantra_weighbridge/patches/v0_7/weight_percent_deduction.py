"""Weighment Slip: "Other Deduction" is now a percentage of the Net Cane Weight (Cane Weight - Binding Material).

Runs after model sync (the new columns exist). For every slip:
- `net_after_binding` (cane weight - binding material) is filled
- an old absolute Other Deduction in Kg is converted into the equivalent percentage, so the slip still
  re-calculates to the same Net Weight if it is amended later. `net_cane_weight` itself is not touched.
"""

import frappe
from frappe.utils import flt


def execute():
	if not frappe.db.has_column("Weighment Slip", "other_deduction_percent"):
		return
	frappe.db.sql("update `tabWeighment Slip` set net_after_binding = greatest(cane_weight - mat_weight, 0)")
	rows = frappe.db.sql(
		"""select name, net_after_binding, other_deduction from `tabWeighment Slip`
		where other_deduction > 0 and ifnull(other_deduction_percent, 0) = 0 and net_after_binding > 0""",
		as_dict=True,
	)
	for r in rows:
		percent = flt(r.other_deduction) * 100 / flt(r.net_after_binding)
		frappe.db.set_value("Weighment Slip", r.name, "other_deduction_percent", percent, update_modified=False)
	frappe.db.commit()
