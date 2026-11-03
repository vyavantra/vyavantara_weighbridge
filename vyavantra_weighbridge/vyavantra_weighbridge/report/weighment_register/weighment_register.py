# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

STATUS = {"Submitted": "= 1", "Cancelled": "= 2", "Draft": "= 0", "All": "in (0, 1, 2)"}
GROUPS = {
	"Date": ("slip_date", "Date", "Date"),
	"Shift": ("shift", "Shift", "Link/Weighbridge Shift"),
	"Village": ("village", "Village", "Link/Village Master"),
	"Cane Supplier": ("farmer", "Cane Supplier", "Link/Cane Supplier"),
	"Vehicle": ("vehicle_no", "Vehicle", "Data"),
	"Delivery Type": ("delivery_type", "Delivery Type", "Data"),
	"Cane Rate": ("cane_rate", "Cane Rate (per Ton)", "Currency"),
	"Deduction Reason": ("deduction_reason", "Reason", "Data"),
	"Transport Contractor": ("transport_contractor", "Transport Contractor", "Link/Contractor Master"),
	"Cutting Contractor": ("cutting_contractor", "Cutting Contractor", "Link/Contractor Master"),
	"Agent": ("agent", "Agent", "Link/Cane Agent"),
}
FILTER_FIELDS = ("shift", "farmer", "village", "vehicle", "delivery_type", "agent")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not (filters.from_date and filters.to_date):
		frappe.throw(_("From Date and To Date are required"))
	where, values = ["slip_date between %(from_date)s and %(to_date)s"], dict(filters)
	where.append(f"docstatus {STATUS.get(filters.status or 'Submitted', STATUS['Submitted'])}")
	for f in FILTER_FIELDS:
		if filters.get(f):
			where.append(f"`{f}` = %({f})s")
	if filters.contractor:
		where.append("(transport_contractor = %(contractor)s or cutting_contractor = %(contractor)s)")
	if filters.slip_no:
		values["slip_like"] = f"%{filters.slip_no}%"
		where.append("(name like %(slip_like)s or serial_no = %(slip_no)s)")
	condition = " and ".join(where)

	group = filters.group_by
	if group and group != "None":
		return grouped(group, condition, values)
	return detail(condition, values)


def detail(condition, values):
	columns = [
		{"label": _("Slip"), "fieldname": "name", "fieldtype": "Link", "options": "Weighment Slip", "width": 140},
		{"label": _("Date"), "fieldname": "slip_date", "fieldtype": "Date", "width": 95},
		{"label": _("Shift"), "fieldname": "shift", "fieldtype": "Link", "options": "Weighbridge Shift", "width": 90},
		{"label": _("Serial"), "fieldname": "serial_no", "fieldtype": "Int", "width": 60},
		{"label": _("Vehicle"), "fieldname": "vehicle_no", "fieldtype": "Data", "width": 110},
		{"label": _("Cane Supplier"), "fieldname": "farmer_name", "fieldtype": "Data", "width": 150},
		{"label": _("Village"), "fieldname": "village", "fieldtype": "Link", "options": "Village Master", "width": 100},
		{"label": _("Delivery"), "fieldname": "delivery_type", "fieldtype": "Data", "width": 110},
		{"label": _("Loaded (Kg)"), "fieldname": "gross_weight", "fieldtype": "Float", "width": 100},
		{"label": _("Empty (Kg)"), "fieldname": "tare_weight", "fieldtype": "Float", "width": 100},
		{"label": _("Cane (Kg)"), "fieldname": "cane_weight", "fieldtype": "Float", "width": 100},
		{"label": _("Binding (Kg)"), "fieldname": "mat_weight", "fieldtype": "Float", "width": 90},
		{"label": _("Other Ded. (%)"), "fieldname": "other_deduction_percent", "fieldtype": "Percent", "width": 90},
		{"label": _("Other Ded. (Kg)"), "fieldname": "other_deduction", "fieldtype": "Float", "width": 100},
		{"label": _("Net Weight (Kg)"), "fieldname": "net_cane_weight", "fieldtype": "Float", "width": 110},
		{"label": _("Rate / Ton"), "fieldname": "cane_rate", "fieldtype": "Currency", "width": 90},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Deduction Reason"), "fieldname": "deduction_reason", "fieldtype": "Data", "width": 160},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
	]
	data = frappe.db.sql(
		f"""select name, slip_date, shift, serial_no, vehicle_no, farmer_name, village, delivery_type,
		gross_weight, tare_weight, cane_weight, mat_weight, other_deduction_percent, other_deduction, net_cane_weight, cane_rate,
		round(net_cane_weight / 1000 * cane_rate, 2) as amount, deduction_reason,
		case docstatus when 0 then 'Draft' when 1 then 'Submitted' else 'Cancelled' end as status
		from `tabWeighment Slip` where {condition} order by slip_date, serial_no, name""",
		values,
		as_dict=True,
	)
	if data:
		total = {"name": _("Total"), "farmer_name": _("{0} trips").format(len(data))}
		for k in ("gross_weight", "tare_weight", "cane_weight", "mat_weight", "other_deduction", "net_cane_weight", "amount"):
			total[k] = flt(sum(flt(d.get(k)) for d in data), 2)
		data.append(total)
	return columns, data


def grouped(group, condition, values):
	field, label, ftype = GROUPS[group]
	extra = " and ifnull(deduction_reason, '') != ''" if group == "Deduction Reason" else ""
	col = {"label": _(label), "fieldname": "grp", "width": 170}
	if "/" in ftype:
		col.update(fieldtype="Link", options=ftype.split("/")[1])
	else:
		col["fieldtype"] = ftype
	columns = [
		col,
		{"label": _("Trips"), "fieldname": "trips", "fieldtype": "Int", "width": 70},
		{"label": _("Loaded (Kg)"), "fieldname": "gross", "fieldtype": "Float", "width": 110},
		{"label": _("Empty (Kg)"), "fieldname": "tare", "fieldtype": "Float", "width": 110},
		{"label": _("Deductions (Kg)"), "fieldname": "deductions", "fieldtype": "Float", "width": 120},
		{"label": _("Net Weight (Kg)"), "fieldname": "net", "fieldtype": "Float", "width": 110},
		{"label": _("Net (Ton)"), "fieldname": "net_ton", "fieldtype": "Float", "precision": 3, "width": 100},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
	]
	data = frappe.db.sql(
		f"""select `{field}` as grp, count(*) as trips, sum(gross_weight) as gross, sum(tare_weight) as tare,
		sum(mat_weight + other_deduction) as deductions, sum(net_cane_weight) as net,
		round(sum(net_cane_weight) / 1000, 3) as net_ton,
		round(sum(net_cane_weight / 1000 * cane_rate), 2) as amount
		from `tabWeighment Slip` where {condition}{extra} group by `{field}` order by `{field}`""",
		values,
		as_dict=True,
	)
	chart = None
	if data:
		points = data[:30]
		chart = {
			"data": {
				"labels": [str(d.grp) if d.grp not in (None, "") else _("(Not set)") for d in points],
				"datasets": [{"name": _("Net (Kg)"), "values": [flt(d.net) for d in points]}],
			},
			"type": "bar",
		}
		total = {"grp": _("Total")}
		for k in ("trips", "gross", "tare", "deductions", "net", "net_ton", "amount"):
			total[k] = flt(sum(flt(d.get(k)) for d in data), 3)
		total["trips"] = int(total["trips"])
		data.append(total)
	return columns, data, None, chart
