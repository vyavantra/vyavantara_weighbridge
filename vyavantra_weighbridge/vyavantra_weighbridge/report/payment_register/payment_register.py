# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Payment"), "fieldname": "name", "fieldtype": "Link", "options": "Weighbridge Payment", "width": 150},
		{"label": _("Date"), "fieldname": "payment_date", "fieldtype": "Date", "width": 95},
		{"label": _("Bill Type"), "fieldname": "bill_doctype", "fieldtype": "Data", "width": 160},
		{"label": _("Bill"), "fieldname": "bill", "fieldtype": "Dynamic Link", "options": "bill_doctype", "width": 150},
		{"label": _("Party"), "fieldname": "party_name", "fieldtype": "Data", "width": 160},
		{"label": _("Mode"), "fieldname": "mode", "fieldtype": "Data", "width": 100},
		{"label": _("Bank"), "fieldname": "bank", "fieldtype": "Link", "options": "Weighbridge Bank", "width": 130},
		{"label": _("Cheque No."), "fieldname": "cheque_no", "fieldtype": "Data", "width": 100},
		{"label": _("Cheque Date"), "fieldname": "cheque_date", "fieldtype": "Date", "width": 95},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Approval"), "fieldname": "approval_status", "fieldtype": "Data", "width": 90},
		{"label": _("Reconciled"), "fieldname": "reconciled", "fieldtype": "Check", "width": 90},
		{"label": _("Clearance Date"), "fieldname": "clearance_date", "fieldtype": "Date", "width": 100},
		{"label": _("Journal Entry"), "fieldname": "journal_entry", "fieldtype": "Link", "options": "Journal Entry", "width": 140},
	]
	cond, values = ["docstatus = 1"], dict(filters)
	if filters.from_date:
		cond.append("payment_date >= %(from_date)s")
	if filters.to_date:
		cond.append("payment_date <= %(to_date)s")
	if filters.mode:
		cond.append("mode = %(mode)s")
	if filters.bill_doctype:
		cond.append("bill_doctype = %(bill_doctype)s")
	if filters.unreconciled:
		cond.append("(mode != 'Cash' and reconciled = 0)")
	data = frappe.db.sql(
		f"""select name, payment_date, bill_doctype, bill, party_name, mode, bank, cheque_no, cheque_date,
		amount, approval_status, reconciled, clearance_date, journal_entry
		from `tabWeighbridge Payment` where {' and '.join(cond)} order by payment_date, name""",
		values,
		as_dict=True,
	)
	if data:
		data.append({"name": _("Total"), "amount": flt(sum(flt(d.amount) for d in data), 2)})
	return columns, data
