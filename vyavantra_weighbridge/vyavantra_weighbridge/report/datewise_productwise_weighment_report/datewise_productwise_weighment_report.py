# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


def execute(filters=None):
	frappe.has_permission("Other Weight", "report", throw=True)
	filters = frappe._dict(filters or {})
	from_date, to_date = getdate(filters.from_date or nowdate()), getdate(filters.to_date or nowdate())
	if from_date > to_date:
		frappe.throw(_("From Date cannot be after To Date"))

	conditions = "o.docstatus = 1 and o.slip_date between %s and %s"
	values = [from_date, to_date]
	if filters.product_name:
		conditions += " and o.product_name = %s"
		values.append(filters.product_name)

	rows = frappe.db.sql(
		f"""select o.product_name, i.item_name product_label, o.slip_date, o.serial_no, o.name slip_name,
			ps.supplier_name party_name, ts.supplier_name transporter, o.place, o.vehicle_type,
			tn.tractor_number vehicle_no, o.loaded_weight, o.empty_weight, o.net_weight, o.clerk
		from `tabOther Weight` o
		left join `tabItem` i on i.name = o.product_name
		left join `tabSupplier` ps on ps.name = o.party_name
		left join `tabSupplier` ts on ts.name = o.transporter
		left join `tabTractor Number` tn on tn.name = o.vehicle_no
		where {conditions}
		order by o.slip_date, i.item_name, o.product_name, o.serial_no, o.name""",
		values, as_dict=True,
	)

	columns = [
		{"fieldname": "slip_no", "label": _("SlipNo"), "fieldtype": "Data", "width": 85},
		{"fieldname": "party_name", "label": _("Party Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "transporter", "label": _("Transporter"), "fieldtype": "Data", "width": 150},
		{"fieldname": "place", "label": _("Place"), "fieldtype": "Data", "width": 100},
		{"fieldname": "vehicle_type", "label": _("Veh Type"), "fieldtype": "Data", "width": 85},
		{"fieldname": "vehicle_no", "label": _("Vehno"), "fieldtype": "Data", "width": 105},
		{"fieldname": "load_wt", "label": _("Load Wt"), "fieldtype": "Float", "precision": 2, "width": 90},
		{"fieldname": "empty_wt", "label": _("Empty Wt"), "fieldtype": "Float", "precision": 2, "width": 90},
		{"fieldname": "net_wt", "label": _("Net Wt"), "fieldtype": "Float", "precision": 2, "width": 90},
		{"fieldname": "clerk", "label": _("Clerk"), "fieldtype": "Data", "width": 70},
	]

	def zero():
		return {"load": 0.0, "empty": 0.0, "net": 0.0}

	def totals_row(label, totals, row_type):
		return {
			"party_name": label,
			"load_wt": round(totals["load"], 2),
			"empty_wt": round(totals["empty"], 2),
			"net_wt": round(totals["net"], 2),
			"row_type": row_type,
		}

	data = []
	current_date, current_product = None, None
	product_total, date_total, grand_total = zero(), zero(), zero()

	def close_product():
		if current_product is not None:
			data.append(totals_row(_("Product Total"), product_total, "product_total"))

	def close_date():
		close_product()
		if current_date is not None:
			data.append(totals_row(_("Date Total"), date_total, "date_total"))

	for r in rows:
		if r.slip_date != current_date:
			close_date()
			current_date, current_product = r.slip_date, None
			date_total = zero()
			data.append({"party_name": _("Date") + " " + r.slip_date.strftime("%d/%m/%Y"), "row_type": "date"})

		label = r.product_label or r.product_name or _("(No Product)")
		if label != current_product:
			close_product()
			current_product = label
			product_total = zero()
			data.append({"party_name": _("Product Name") + ": " + label, "row_type": "product"})

		load, empty, net = flt(r.loaded_weight), flt(r.empty_weight), flt(r.net_weight)
		for bucket in (product_total, date_total, grand_total):
			bucket["load"] += load
			bucket["empty"] += empty
			bucket["net"] += net

		data.append({
			"slip_no": r.serial_no or r.slip_name,
			"party_name": r.party_name or "",
			"transporter": r.transporter or "",
			"place": r.place or "",
			"vehicle_type": r.vehicle_type or "",
			"vehicle_no": r.vehicle_no or "",
			"load_wt": load,
			"empty_wt": empty,
			"net_wt": net,
			"clerk": r.clerk or "",
			"row_type": "slip",
		})

	close_date()
	if rows:
		data.append(totals_row(_("Grand Total"), grand_total, "total"))

	return columns, data
