# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Bill"), "fieldname": "name", "fieldtype": "Link", "options": "Agent Bill", "width": 150},
		{"label": _("Bill Date"), "fieldname": "bill_date", "fieldtype": "Date", "width": 95},
		{"label": _("Agent No."), "fieldname": "agent", "fieldtype": "Link", "options": "Cane Agent", "width": 100},
		{"label": _("Agent Name"), "fieldname": "agent_name", "fieldtype": "Data", "width": 170},
		{"label": _("From"), "fieldname": "from_date", "fieldtype": "Date", "width": 90},
		{"label": _("To"), "fieldname": "to_date", "fieldtype": "Date", "width": 90},
		{"label": _("Cane (Ton)"), "fieldname": "total_quantity", "fieldtype": "Float", "precision": 3, "width": 100},
		{"label": _("Commission Rate"), "fieldname": "commission_rate", "fieldtype": "Currency", "width": 110},
		{"label": _("Commission"), "fieldname": "total_amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Deductions"), "fieldname": "total_deductions", "fieldtype": "Currency", "width": 110},
		{"label": _("Net Payable"), "fieldname": "net_payable", "fieldtype": "Currency", "width": 110},
		{"label": _("Paid"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 100},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Status"), "fieldname": "payment_status", "fieldtype": "Data", "width": 100},
	]
	cond, values = ["docstatus = 1"], dict(filters)
	if filters.agent:
		cond.append("agent = %(agent)s")
	if filters.from_date:
		cond.append("bill_date >= %(from_date)s")
	if filters.to_date:
		cond.append("bill_date <= %(to_date)s")
	data = frappe.db.sql(
		f"""select name, bill_date, agent, agent_name, from_date, to_date, total_quantity, commission_rate,
		total_amount, total_deductions, net_payable, paid_amount, outstanding_amount, payment_status
		from `tabAgent Bill` where {' and '.join(cond)} order by bill_date, name""",
		values,
		as_dict=True,
	)
	if data:
		total = {"name": _("Total")}
		for k in ("total_quantity", "total_amount", "total_deductions", "net_payable", "paid_amount", "outstanding_amount"):
			total[k] = flt(sum(flt(d.get(k)) for d in data), 3 if k == "total_quantity" else 2)
		data.append(total)
	return columns, data
