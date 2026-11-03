# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from vyavantra_weighbridge.report_utils import GROUPS, check_access, group_of, tons


def execute(filters=None):
	check_access()
	filters = frappe._dict(filters or {})
	from_date, to_date = getdate(filters.from_date or nowdate()), getdate(filters.to_date or nowdate())
	if from_date > to_date:
		frappe.throw(_("From Date cannot be after To Date"))
	rows = frappe.db.sql(
		"""select delivery_type, count(*) nos, sum(net_cane_weight) kg from `tabWeighment Slip`
		where docstatus = 1 and net_cane_weight > 0 and slip_date between %s and %s group by delivery_type""",
		(from_date, to_date), as_dict=True,
	)
	acc = {g: [0, 0.0] for g in GROUPS}
	for r in rows:
		a = acc[group_of(r.delivery_type)]
		a[0] += r.nos
		a[1] += r.kg or 0
	columns = [
		{"fieldname": "delivery_type", "label": _("Delivery Type"), "fieldtype": "Data", "width": 200},
		{"fieldname": "nos", "label": _("Nos"), "fieldtype": "Int", "width": 100},
		{"fieldname": "tonnage", "label": _("Tonnage"), "fieldtype": "Float", "precision": 3, "width": 140},
	]
	data = [{"delivery_type": g, "nos": acc[g][0], "tonnage": tons(acc[g][1])} for g in GROUPS]
	data.append({"delivery_type": _("Total"), "nos": sum(r["nos"] for r in data), "tonnage": round(sum(r["tonnage"] for r in data), 3)})
	return columns, data
