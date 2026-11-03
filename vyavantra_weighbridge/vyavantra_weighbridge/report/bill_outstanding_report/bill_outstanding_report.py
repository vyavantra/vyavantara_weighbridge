# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

BILLS = {
	"Farmer": ("Farmer Bill", "farmer", "farmer_name"),
	"Tractor Contractor": ("Tractor Contractor Bill", "contractor", "contractor_name"),
	"Todani Contractor": ("Todani Contractor Bill", "contractor", "contractor_name"),
	"Agent": ("Agent Bill", "agent", "agent_name"),
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	kinds = [filters.bill_type] if filters.bill_type and filters.bill_type != "All" else list(BILLS)
	columns = [
		{"label": _("Bill Type"), "fieldname": "bill_type", "fieldtype": "Data", "width": 140},
		{"label": _("Bill"), "fieldname": "bill", "fieldtype": "Dynamic Link", "options": "doctype", "width": 150},
		{"label": _("Bill Date"), "fieldname": "bill_date", "fieldtype": "Date", "width": 95},
		{"label": _("Party No."), "fieldname": "party", "fieldtype": "Data", "width": 100},
		{"label": _("Party Name"), "fieldname": "party_name", "fieldtype": "Data", "width": 180},
		{"label": _("Quantity (Ton)"), "fieldname": "qty", "fieldtype": "Float", "precision": 3, "width": 110},
		{"label": _("Total Amount"), "fieldname": "total_amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Deductions"), "fieldname": "total_deductions", "fieldtype": "Currency", "width": 110},
		{"label": _("Net Payable"), "fieldname": "net_payable", "fieldtype": "Currency", "width": 110},
		{"label": _("Paid"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Status"), "fieldname": "payment_status", "fieldtype": "Data", "width": 100},
	]
	data = []
	for kind in kinds:
		doctype, party_f, name_f = BILLS[kind]
		cond, values = ["docstatus = 1"], {}
		if filters.from_date:
			cond.append("bill_date >= %(from_date)s")
			values["from_date"] = filters.from_date
		if filters.to_date:
			cond.append("bill_date <= %(to_date)s")
			values["to_date"] = filters.to_date
		if filters.party:
			cond.append(f"`{party_f}` = %(party)s")
			values["party"] = filters.party
		if filters.only_outstanding:
			cond.append("outstanding_amount > 0")
		for r in frappe.db.sql(
			f"""select name as bill, bill_date, `{party_f}` as party, `{name_f}` as party_name,
			total_quantity as qty, total_amount, total_deductions, net_payable, paid_amount,
			outstanding_amount, payment_status from `tab{doctype}` where {' and '.join(cond)}
			order by bill_date, name""",
			values,
			as_dict=True,
		):
			r.update(bill_type=kind, doctype=doctype)
			data.append(r)
	if data:
		total = {"bill_type": _("Total")}
		for k in ("qty", "total_amount", "total_deductions", "net_payable", "paid_amount", "outstanding_amount"):
			total[k] = flt(sum(flt(d.get(k)) for d in data), 3 if k == "qty" else 2)
		data.append(total)
	return columns, data
