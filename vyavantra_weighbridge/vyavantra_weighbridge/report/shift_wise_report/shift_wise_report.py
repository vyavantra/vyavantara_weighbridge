# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate

from vyavantra_weighbridge.report_utils import GROUPS, check_access, fmt_date, group_of, tons

SHIFT_LABELS = ("First Shift", "Second Shift", "Third Shift")


def execute(filters=None):
	check_access()
	filters = frappe._dict(filters or {})
	report_date = getdate(filters.report_date or nowdate())
	start = getdate(filters.season_start) if filters.season_start else default_season_start(report_date)
	shifts = frappe.get_all("Weighbridge Shift", filters={"disabled": 0}, pluck="name", order_by="start_time asc, name asc")[:3]

	rows = frappe.db.sql(
		"""select slip_date, ifnull(shift, '') shift, delivery_type, count(*) nos, sum(net_cane_weight) kg
		from `tabWeighment Slip`
		where docstatus = 1 and net_cane_weight > 0 and slip_date between %s and %s
		group by slip_date, shift, delivery_type""",
		(start, report_date), as_dict=True,
	)
	keys = ["s%d" % i for i in range(3)] + ["today", "yest", "todate"]
	acc = {g: {k: [0, 0.0] for k in keys} for g in GROUPS}
	for r in rows:
		a = acc[group_of(r.delivery_type)]
		cells = ["todate"]
		if r.slip_date == report_date:
			cells.append("today")
			if r.shift in shifts:
				cells.append("s%d" % shifts.index(r.shift))
		else:
			cells.append("yest")
		for c in cells:
			a[c][0] += r.nos
			a[c][1] += r.kg or 0

	columns = [{"fieldname": "vehicle_type", "label": _("Vehicle Type"), "fieldtype": "Data", "width": 160}]
	for k, label in zip(keys, list(SHIFT_LABELS) + ["Today", "Till Yesterday", "To Date"]):
		columns += [
			{"fieldname": k + "_nos", "label": _("{0} - Nos").format(_(label)), "fieldtype": "Int", "width": 90},
			{"fieldname": k + "_ton", "label": _("{0} - Tonnage").format(_(label)), "fieldtype": "Float", "precision": 3, "width": 120},
		]
	data, total = [], {"vehicle_type": _("Total")}
	for g in GROUPS:
		row = {"vehicle_type": g}
		for k in keys:
			row[k + "_nos"], row[k + "_ton"] = acc[g][k][0], tons(acc[g][k][1])
			total[k + "_nos"] = total.get(k + "_nos", 0) + acc[g][k][0]
			total[k + "_ton"] = round(total.get(k + "_ton", 0) + tons(acc[g][k][1]), 3)
		data.append(row)
	data.append(total)
	return columns, data


def default_season_start(d):
	"""Sugar season starts on 1 October."""
	return getdate("%s-10-01" % (d.year if d.month >= 10 else d.year - 1))
