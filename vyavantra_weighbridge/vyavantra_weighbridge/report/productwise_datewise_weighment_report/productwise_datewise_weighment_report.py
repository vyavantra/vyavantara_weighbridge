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
			tn.tractor_number vehicle_no, o.loaded_weight, o.empty_weight, o.net_weight
		from `tabOther Weight` o
		left join `tabItem` i on i.name = o.product_name
		left join `tabSupplier` ps on ps.name = o.party_name
		left join `tabSupplier` ts on ts.name = o.transporter
		left join `tabTractor Number` tn on tn.name = o.vehicle_no
		where {conditions}
		order by i.item_name, o.product_name, o.slip_date, o.serial_no, o.name""",
		values, as_dict=True,
	)

	columns = [
		{"fieldname": "slip_date", "label": _("Date"), "fieldtype": "Date", "width": 95},
		{"fieldname": "slip_no", "label": _("SlipNo"), "fieldtype": "Data", "width": 85},
		{"fieldname": "party_name", "label": _("Party Name"), "fieldtype": "Data", "width": 160},
		{"fieldname": "transporter", "label": _("Transporter"), "fieldtype": "Data", "width": 160},
		{"fieldname": "place", "label": _("Place"), "fieldtype": "Data", "width": 110},
		{"fieldname": "vehicle_type", "label": _("Veh Type"), "fieldtype": "Data", "width": 90},
		{"fieldname": "vehicle_no", "label": _("Vehno"), "fieldtype": "Data", "width": 110},
		{"fieldname": "load_wt", "label": _("Load Wt"), "fieldtype": "Float", "precision": 2, "width": 95},
		{"fieldname": "empty_wt", "label": _("Empty Wt"), "fieldtype": "Float", "precision": 2, "width": 95},
		{"fieldname": "net_wt", "label": _("Net Wt"), "fieldtype": "Float", "precision": 2, "width": 95},
	]

	data = []
	current_product = None
	product_total = {"load": 0.0, "empty": 0.0, "net": 0.0}
	grand_total = {"load": 0.0, "empty": 0.0, "net": 0.0}

	def close_product():
		if current_product is None:
			return
		data.append({
			"party_name": _("Productwise Total"),
			"load_wt": round(product_total["load"], 2),
			"empty_wt": round(product_total["empty"], 2),
			"net_wt": round(product_total["net"], 2),
			"row_type": "subtotal",
		})

	for r in rows:
		label = r.product_label or r.product_name or _("(No Product)")
		if label != current_product:
			close_product()
			current_product = label
			product_total = {"load": 0.0, "empty": 0.0, "net": 0.0}
			data.append({"party_name": _("Product Name") + ": " + label, "row_type": "product"})

		load, empty, net = flt(r.loaded_weight), flt(r.empty_weight), flt(r.net_weight)
		product_total["load"] += load
		product_total["empty"] += empty
		product_total["net"] += net
		grand_total["load"] += load
		grand_total["empty"] += empty
		grand_total["net"] += net

		data.append({
			"slip_date": r.slip_date,
			"slip_no": r.serial_no or r.slip_name,
			"party_name": r.party_name or "",
			"transporter": r.transporter or "",
			"place": r.place or "",
			"vehicle_type": r.vehicle_type or "",
			"vehicle_no": r.vehicle_no or "",
			"load_wt": load,
			"empty_wt": empty,
			"net_wt": net,
			"row_type": "slip",
		})

	close_product()
	if rows:
		data.append({
			"party_name": _("Grand Total"),
			"load_wt": round(grand_total["load"], 2),
			"empty_wt": round(grand_total["empty"], 2),
			"net_wt": round(grand_total["net"], 2),
			"row_type": "total",
		})

	return columns, data
