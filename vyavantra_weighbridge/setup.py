# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

"""Roles, default shifts, dashboard cards/charts and workspace sections for the weighbridge module.

Everything here is idempotent. Existing workspace content is never changed, only appended to.
"""

import json

import frappe

MODULE = "Vyavantra Weighbridge"
WORKSPACE = "Vyavantra Weighbridge"
ROLES = ("Weighbridge Manager", "Weighbridge User", "Chit Boy")
SHIFTS = (
	("Shift 1", "04:00:00", "12:00:00"),
	("Shift 2", "12:00:00", "20:00:00"),
	("Shift 3", "20:00:00", "04:00:00"),
)


def after_install():
	ensure_roles()
	after_migrate_setup()


def ensure_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


def after_migrate_setup():
	ensure_roles()
	create_shifts()
	ensure_bank_fields()
	seed_varieties()
	seed_delivery_types()
	set_default_print_formats()
	create_dashboard()
	rebuild_workspace()
	frappe.db.commit()


# A standard DocType cannot carry `default_print_format` in its JSON (DocType.validate throws), so it is
# applied as a Property Setter, which is what Customize Form creates.
DEFAULT_PRINT_FORMATS = (
	("Weighment Slip", "Weighment Slip Print"),
	("General Weighment Slip", "General Weighment Slip Print"),
)


def set_default_print_formats():
	for doctype, print_format in DEFAULT_PRINT_FORMATS:
		if not (frappe.db.exists("DocType", doctype) and frappe.db.exists("Print Format", print_format)):
			continue
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"doctype_or_field": "DocType",
				"property": "default_print_format",
				"value": print_format,
				"property_type": "Data",
			}
		)


def create_shifts():
	if not frappe.db.exists("DocType", "Weighbridge Shift"):
		return
	for name, start, end in SHIFTS:
		if not frappe.db.exists("Weighbridge Shift", name):
			frappe.get_doc(
				{"doctype": "Weighbridge Shift", "shift_name": name, "start_time": start, "end_time": end}
			).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------- dashboard
CARDS = (
	# label, doctype, function, field, filters, dynamic filters, color
	("Today's Net Cane (Kg)", "Weighment Slip", "Sum", "net_cane_weight",
	 [["Weighment Slip", "docstatus", "=", 1]], {"slip_date": "frappe.datetime.get_today()"}, "#2490EF"),
	("Today's Vehicle Trips", "Weighment Slip", "Count", None,
	 [["Weighment Slip", "docstatus", "=", 1]], {"slip_date": "frappe.datetime.get_today()"}, "#29CD42"),
	("Total Net Cane (Kg)", "Weighment Slip", "Sum", "net_cane_weight",
	 [["Weighment Slip", "docstatus", "=", 1]], None, "#2490EF"),
	("Cancelled Weighment Slips", "Weighment Slip", "Count", None,
	 [["Weighment Slip", "docstatus", "=", 2]], None, "#ED6396"),
	("Farmer Outstanding", "Farmer Bill", "Sum", "outstanding_amount",
	 [["Farmer Bill", "docstatus", "=", 1]], None, "#F8814F"),
	("Tractor Contractor Outstanding", "Tractor Contractor Bill", "Sum", "outstanding_amount",
	 [["Tractor Contractor Bill", "docstatus", "=", 1]], None, "#F8814F"),
	("Todani Contractor Outstanding", "Todani Contractor Bill", "Sum", "outstanding_amount",
	 [["Todani Contractor Bill", "docstatus", "=", 1]], None, "#F8814F"),
	("Agent Outstanding", "Agent Bill", "Sum", "outstanding_amount",
	 [["Agent Bill", "docstatus", "=", 1]], None, "#F8814F"),
	("Payments Pending Approval", "Weighbridge Payment", "Count", None,
	 [["Weighbridge Payment", "docstatus", "=", 0], ["Weighbridge Payment", "approval_status", "=", "Pending"]],
	 None, "#ECAD4B"),
)


def _dt_exists(doctype):
	return bool(frappe.db.exists("DocType", doctype))


def create_dashboard():
	names = []
	for label, doctype, fn, field, filters, dyn, color in CARDS:
		if not _dt_exists(doctype):
			continue
		names.append(label)
		if frappe.db.exists("Number Card", label):
			continue
		card = {
			"doctype": "Number Card", "name": label, "label": label, "type": "Document Type",
			"document_type": doctype, "function": fn, "color": color, "is_public": 1, "show_percentage_stats": 0,
			"filters_json": json.dumps(filters), "module": MODULE,
		}
		if field:
			card["aggregate_function_based_on"] = field
		if dyn:
			card["dynamic_filters_json"] = json.dumps(dyn)
		frappe.get_doc(card).insert(ignore_permissions=True)

	charts = (
		("Daily Cane Weight (Kg)", {"chart_type": "Sum", "based_on": "slip_date",
									"value_based_on": "net_cane_weight", "timespan": "Last Month",
									"time_interval": "Daily", "timeseries": 1, "type": "Bar"}),
		("Village-wise Cane Supply (Kg)", {"chart_type": "Group By", "group_by_type": "Sum",
										  "group_by_based_on": "village", "aggregate_function_based_on": "net_cane_weight",
										  "number_of_groups": 10, "type": "Bar"}),
	)
	for label, cfg in charts:
		if frappe.db.exists("Dashboard Chart", label) or not _dt_exists("Weighment Slip"):
			continue
		frappe.get_doc({
			"doctype": "Dashboard Chart", "name": label, "chart_name": label, "document_type": "Weighment Slip",
			"filters_json": json.dumps([["Weighment Slip", "docstatus", "=", 1]]), "is_public": 1,
			"is_custom": 0, "module": MODULE, "color": "#2490EF", **cfg,
		}).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------- workspace
SECTIONS = (
	("Weighment", (
		("Weighment Slip", "DocType", "Weighment Slip", "List"),
		("General Weighment Slip", "DocType", "General Weighment Slip", "List"),
	)),
	("Billing", (
		("Farmer Bill", "DocType", "Farmer Bill", "List"),
		("Tractor Contractor Bill", "DocType", "Tractor Contractor Bill", "List"),
		("Todani Contractor Bill", "DocType", "Todani Contractor Bill", "List"),
		("Agent Bill", "DocType", "Agent Bill", "List"),
	)),
	("Accounting & Payments", (
		("Weighbridge Payment", "DocType", "Weighbridge Payment", "List"),
		("Advance / Deposit", "DocType", "Weighbridge Advance", "List"),
	)),
	("Weighbridge Masters", (
		("Village Master", "DocType", "Village Master", "List"),
		("Taluka Master", "DocType", "Taluka Master", "List"),
		("District Master", "DocType", "District Master", "List"),
		("Distance Master", "DocType", "Distance Master", "List"),
		("Route Master", "DocType", "Route Master", "List"),
		("Cane Supplier", "DocType", "Cane Supplier", "List"),
		("Cane Variety", "DocType", "Cane Variety", "List"),
		("Delivery Type", "DocType", "Delivery Type", "List"),
		("Cane Rate Master", "DocType", "Cane Rate Master", "List"),
		("Contractor Master", "DocType", "Contractor Master", "List"),
		("Tractor Number", "DocType", "Tractor Number", "List"),
		("Agent Master", "DocType", "Cane Agent", "List"),
		("Bank", "DocType", "Bank", "List"),
		("Shift Master", "DocType", "Weighbridge Shift", "List"),
		("Weighbridge Settings", "DocType", "Weighbridge Settings", "List"),
	)),
	("Weighbridge Reports", (
		("Weighment Register", "Report", "Weighment Register", None),
		("Cancelled Weighment Slips", "Report", "Cancelled Weighment Slips", None),
		("Bill Outstanding Report", "Report", "Bill Outstanding Report", None),
		("Agent Commission Report", "Report", "Agent Commission Report", None),
		("Payment Register", "Report", "Payment Register", None),
	)),
)


def extend_workspace():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	ws = frappe.get_doc("Workspace", WORKSPACE)
	content = json.loads(ws.content or "[]")
	if any(b.get("id") == "wbreq_hdr_dash" for b in content):
		return  # already extended
	existing = {s.label for s in ws.shortcuts}

	blocks = [{"id": "wbreq_hdr_dash", "type": "header",
			   "data": {"text": '<span class="h4"><b>Weighbridge Dashboard</b></span>', "col": 12}}]
	for i, (label, *_rest) in enumerate(CARDS):
		if frappe.db.exists("Number Card", label):
			if not any(c.label == label for c in ws.number_cards):
				ws.append("number_cards", {"label": label, "number_card_name": label})
			blocks.append({"id": f"wbreq_nc{i}", "type": "number_card", "data": {"number_card_name": label, "col": 4}})
	for i, label in enumerate(("Daily Cane Weight (Kg)", "Village-wise Cane Supply (Kg)")):
		if frappe.db.exists("Dashboard Chart", label):
			if not any(c.chart_name == label for c in ws.charts):
				ws.append("charts", {"label": label, "chart_name": label})
			blocks.append({"id": f"wbreq_ch{i}", "type": "chart", "data": {"chart_name": label, "col": 6}})

	for si, (title, items) in enumerate(SECTIONS):
		blocks.append({"id": f"wbreq_hdr{si}", "type": "header",
					   "data": {"text": f'<span class="h4"><b>{title}</b></span>', "col": 12}})
		for ii, (label, kind, target, view) in enumerate(items):
			exists = frappe.db.exists("DocType" if kind == "DocType" else "Report", target)
			if not exists:
				continue
			if label not in existing:
				row = {"label": label, "type": kind, "link_to": target, "color": "Grey"}
				if view:
					row["doc_view"] = view
				ws.append("shortcuts", row)
			blocks.append({"id": f"wbreq_sc{si}_{ii}", "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
		blocks.append({"id": f"wbreq_sp{si}", "type": "spacer", "data": {"col": 12}})

	ws.content = json.dumps(content + blocks)
	ws.flags.ignore_links = True
	ws.save(ignore_permissions=True)


OLD_SHORTCUT_LABELS = {"Cane Farmer", "Bank Master", "Vehicle Master"}
DELIVERY_TYPES = ("Farm Delivery", "Gate Cane", "Harvesting Machine")
VARIETIES = ("86032", "265", "10001", "15012", "671", "9805", "8005", "419", "0265")


def ensure_bank_fields():
	"""IFSC code and address on the core Bank doctype (the weighbridge uses Bank, not its own bank master)."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Bank": [
		{"fieldname": "ifsc_code", "fieldtype": "Data", "label": "IFSC Code", "insert_after": "bank_name",
		 "in_list_view": 1},
		{"fieldname": "bank_address", "fieldtype": "Small Text", "label": "Address", "insert_after": "ifsc_code"},
	]}, ignore_validate=True)


def seed_varieties():
	if not frappe.db.exists("DocType", "Cane Variety"):
		return
	for v in VARIETIES:
		if not frappe.db.exists("Cane Variety", v):
			frappe.get_doc({"doctype": "Cane Variety", "variety_name": v}).insert(ignore_permissions=True)


def seed_delivery_types():
	if not frappe.db.exists("DocType", "Delivery Type"):
		return
	for d in DELIVERY_TYPES:
		if not frappe.db.exists("Delivery Type", d):
			frappe.get_doc({"doctype": "Delivery Type", "delivery_type_name": d}).insert(ignore_permissions=True)


def rebuild_workspace():
	"""Re-create the blocks and shortcuts this module added; the original workspace content is left alone."""
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	ws = frappe.get_doc("Workspace", WORKSPACE)
	ours = {label for _t, items in SECTIONS for label, *_ in items} | OLD_SHORTCUT_LABELS
	ws.content = json.dumps([b for b in json.loads(ws.content or "[]") if not str(b.get("id", "")).startswith("wbreq_")])
	ws.shortcuts = [s for s in ws.shortcuts if s.label not in ours]
	ws.flags.ignore_links = True
	ws.save(ignore_permissions=True)
	extend_workspace()
