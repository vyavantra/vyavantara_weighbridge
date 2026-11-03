# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

"""Roles, default shifts, dashboard cards/charts and workspace sections for the weighbridge module.

Everything here is idempotent. Existing workspace content is never changed, only appended to.
"""

import json

import frappe

MODULE = "Vyavantra Weighbridge"
WORKSPACE = "Vyavantra Weighbridge"
ROLES = ("Weighbridge Manager", "Weighbridge User")
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
	seed_report_heading()
	create_message_templates()
	create_dashboard()
	rebuild_workspace()
	create_dashboard_workspace()
	set_default_print_formats()
	frappe.db.commit()


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
	("Weighment", (("Weighment Slip", "DocType", "Weighment Slip", "List"),)),
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
		("Cane Rate Master", "DocType", "Cane Rate Master", "List"),
		("Contractor Master", "DocType", "Contractor Master", "List"),
		("Vehicle Master", "DocType", "Weighbridge Vehicle", "List"),
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
		("Shift Wise Report", "Report", "Shift Wise Report", None),
		("Datewise Report", "Report", "Datewise Report", None),
		("Datewise Crushing Report", "Report", "Datewise Crushing Report", None),
	)),
)


def extend_workspace():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	ws = frappe.get_doc("Workspace", WORKSPACE)
	content = json.loads(ws.content or "[]")
	if any(str(b.get("id", "")).startswith("wbreq_hdr0") for b in content):
		return  # already extended
	existing = {s.label for s in ws.shortcuts}

	blocks = []

	for si, (title, items) in enumerate(SECTIONS):
		blocks.append({"id": f"wbreq_hdr{si}", "type": "custom_block",
					   "data": {"custom_block_name": divider_block(title), "col": 12}})
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

	banner = [{"id": "wbreq_banner", "type": "custom_block", "data": {"custom_block_name": banner_block(), "col": 12}}]
	ws.content = json.dumps(banner + content + blocks)
	sync_custom_blocks(ws)
	ws.flags.ignore_links = True
	ws.save(ignore_permissions=True)


OLD_SHORTCUT_LABELS = {"Cane Farmer", "Bank Master"}
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


def rebuild_workspace():
	"""Re-create the blocks and shortcuts this module added; the original workspace content is left alone."""
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	ws = frappe.get_doc("Workspace", WORKSPACE)
	ours = {label for _t, items in SECTIONS for label, *_ in items} | OLD_SHORTCUT_LABELS
	ws.content = json.dumps(restyle_headers([b for b in json.loads(ws.content or "[]") if not str(b.get("id", "")).startswith("wbreq_")]))
	ws.shortcuts = [s for s in ws.shortcuts if s.label not in ours]
	ws.number_cards = []
	ws.charts = []
	ws.flags.ignore_links = True
	ws.save(ignore_permissions=True)
	extend_workspace()


def seed_report_heading():
	"""Default heading printed on the weighbridge reports; editable in Weighbridge Settings."""
	s = frappe.get_doc("Weighbridge Settings")
	if s.report_company_name == "Diamond Agro Industry":
		s.report_company_name = "Rajdatta Agro Industry"
		s.flags.ignore_mandatory = True
		s.save(ignore_permissions=True)
		return
	if s.report_company_name or s.report_address:
		return
	s.report_company_name = "Rajdatta Agro Industry"
	s.report_address = "GAT NO 584, AP POST APSHINGE (RAHIMATPUR) TQ.KOREGAON DIST. SATARA, MAHARASHTRA 415501"
	s.report_phone = "9423866719"
	s.flags.ignore_mandatory = True
	s.save(ignore_permissions=True)


MARATHI_TEMPLATES = {
	"Weighment Slip - Marathi": (
		"वजन पावती {{ doc.name }}",
		"<p>नमस्कार {{ doc.farmer_name }},</p>"
		"<p>आपल्या वाहन क्र. <b>{{ doc.vehicle }}</b> चे वजन पावती क्र. <b>{{ doc.name }}</b> "
		"दिनांक {{ frappe.utils.formatdate(doc.slip_date, 'dd/MM/yyyy') }} रोजी नोंदविण्यात आले आहे.</p>"
		"<p>एकूण (भरलेले) वजन: {{ '%.3f' % ((doc.gross_weight or 0) / 1000) }} मे. टन<br>"
		"वाहनाचे (रिकामे) वजन: {{ '%.3f' % ((doc.tare_weight or 0) / 1000) }} मे. टन<br>"
		"<b>निव्वळ ऊस वजन: {{ '%.3f' % ((doc.net_cane_weight or 0) / 1000) }} मे. टन</b></p>"
		"<p>धन्यवाद.</p>",
	),
	"Farmer Bill - Marathi": (
		"ऊस बिल {{ doc.name }}",
		"<p>नमस्कार {{ doc.farmer_name }},</p>"
		"<p>आपले ऊस बिल क्र. <b>{{ doc.name }}</b> दिनांक {{ frappe.utils.formatdate(doc.bill_date, 'dd/MM/yyyy') }} "
		"रोजी तयार झाले आहे.</p>"
		"<p>कालावधी: {{ frappe.utils.formatdate(doc.from_date, 'dd/MM/yyyy') }} ते "
		"{{ frappe.utils.formatdate(doc.to_date, 'dd/MM/yyyy') }}<br>"
		"एकूण ऊस: {{ '%.3f' % (doc.total_quantity or 0) }} मे. टन<br>"
		"एकूण रक्कम: ₹ {{ '%.2f' % (doc.total_amount or 0) }}<br>"
		"एकूण कपात: ₹ {{ '%.2f' % (doc.total_deductions or 0) }}<br>"
		"<b>देय रक्कम: ₹ {{ '%.2f' % (doc.net_payable or 0) }}</b></p>"
		"<p>धन्यवाद.</p>",
	),
	"Weighbridge Payment - Marathi": (
		"पेमेंट पावती {{ doc.name }}",
		"<p>नमस्कार {{ doc.party_name }},</p>"
		"<p>बिल क्र. <b>{{ doc.bill }}</b> साठी ₹ <b>{{ '%.2f' % (doc.amount or 0) }}</b> चे पेमेंट "
		"({{ doc.mode }}) दिनांक {{ frappe.utils.formatdate(doc.payment_date, 'dd/MM/yyyy') }} रोजी अदा करण्यात आले आहे.</p>"
		"{% if doc.cheque_no %}<p>चेक क्र.: {{ doc.cheque_no }}</p>{% endif %}"
		"{% if doc.reference_no %}<p>संदर्भ क्र.: {{ doc.reference_no }}</p>{% endif %}"
		"<p>धन्यवाद.</p>",
	),
}


def create_message_templates():
	"""Marathi message templates (Email Template) for the weighment slip, farmer bill and payment."""
	for name, (subject, body) in MARATHI_TEMPLATES.items():
		if frappe.db.exists("Email Template", name):
			continue
		frappe.get_doc({"doctype": "Email Template", "name": name, "subject": subject, "use_html": 1,
						"response_html": body, "response": body}).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------- Dashboard workspace
DASH = "Dashboard"
CHARTS = ("Daily Cane Weight (Kg)", "Village-wise Cane Supply (Kg)")
# doctype -> print format used by the Print button and the PDF download
PRINT_FORMATS = {
	"Weighment Slip": "Weighment Slip Print",
	"Weighbridge Payment": "Cheque Issue Voucher",
	"Diesel Issue Entry": "Diesel Issue Slip",
	"Farmer Bill": "Farmer Bill Print",
	"Tractor Contractor Bill": "Tractor Contractor Bill Print",
	"Todani Contractor Bill": "Todani Contractor Bill Print",
	"Agent Bill": "Agent Bill Print",
	"Weighbridge Advance": "Weighbridge Advance Print",
}


def _tpl(name):
	with open(frappe.get_app_path("vyavantra_weighbridge", "templates", "dashboard", name), encoding="utf-8") as f:
		return f.read()


def create_dashboard_workspace():
	"""Custom HTML Block (KPIs, trend, shifts, villages, recent slips) shown on its own first workspace."""
	block = "Weighbridge Dashboard"
	vals = {"html": _tpl("dash.html"), "style": _tpl("dash.css"), "script": _tpl("dash.js"), "private": 0}
	divider_block("Interactive Charts")
	if frappe.db.exists("Custom HTML Block", block):
		doc = frappe.get_doc("Custom HTML Block", block)
		doc.update(vals)
		doc.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "Custom HTML Block", "name": block, **vals}).insert(ignore_permissions=True)

	content = [
		{"id": "dash_main", "type": "custom_block", "data": {"custom_block_name": block, "col": 12}},
		{"id": "dash_hdr", "type": "custom_block", "data": {"custom_block_name": divider_block("Interactive Charts"), "col": 12}},
	]
	charts = []
	for i, label in enumerate(CHARTS):
		if frappe.db.exists("Dashboard Chart", label):
			charts.append({"label": label, "chart_name": label})
			content.append({"id": f"dash_ch{i}", "type": "chart", "data": {"chart_name": label, "col": 6}})
	content.append({"id": "dash_sp", "type": "spacer", "data": {"col": 12}})

	if frappe.db.exists("Workspace", DASH):
		ws = frappe.get_doc("Workspace", DASH)
	else:
		ws = frappe.new_doc("Workspace")
		ws.name = DASH
	ws.update({"label": DASH, "title": DASH, "public": 1, "is_hidden": 0, "icon": "dashboard", "indicator_color": "blue",
			   "module": MODULE, "sequence_id": 0.5, "description": "Weighbridge operations at a glance",
			   "content": json.dumps(content)})
	sync_custom_blocks(ws, content)
	ws.charts = []
	for c in charts:
		ws.append("charts", c)
	ws.flags.ignore_links = True
	ws.save(ignore_permissions=True)


def set_default_print_formats():
	"""Print button / PDF of these documents use the custom print format by default."""
	for doctype, fmt in PRINT_FORMATS.items():
		if not (frappe.db.exists("DocType", doctype) and frappe.db.exists("Print Format", fmt)):
			continue
		name = f"{doctype}-main-default_print_format"
		if frappe.db.exists("Property Setter", name):
			frappe.db.set_value("Property Setter", name, "value", fmt)
		else:
			frappe.make_property_setter({"doctype": doctype, "doctype_or_field": "DocType", "property": "default_print_format",
										 "value": fmt, "property_type": "Data"}, ignore_validate=True)


# ---------------------------------------------------------------------------- shared look: section dividers and banner
DIVIDERS = {
	"Diesel Management": ("\u26FD", "OPERATIONS"), "Master Data": ("\u25A6", "CONFIGURATION"),
	"Weighment": ("\u2696", "OPERATIONS"), "Billing": ("\u25A4", "BILLS"),
	"Accounting & Payments": ("\u20B9", "ACCOUNTS"), "Weighbridge Masters": ("\u25A6", "CONFIGURATION"),
	"Weighbridge Reports": ("\u25A4", "REPORTS"), "Interactive Charts": ("\u25D4", "ANALYTICS"),
}


def _upsert_block(name, html, style, script=""):
	vals = {"html": html, "style": style, "script": script, "private": 0}
	if frappe.db.exists("Custom HTML Block", name):
		doc = frappe.get_doc("Custom HTML Block", name)
		doc.update(vals)
		doc.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "Custom HTML Block", "name": name, **vals}).insert(ignore_permissions=True)
	return name


def divider_block(title):
	"""Same section heading as the Rajdatta Agro Industry workspace (line - title chip - line)."""
	icon, status = DIVIDERS.get(title, ("\u25A6", "WEIGHBRIDGE"))
	title_html = frappe.utils.escape_html(title).upper()
	html = (f'<div class="wbs"><span class="line"></span><div class="sh"><span class="ic">{icon}</span><b>{title_html}</b>'
			f'<em><i class="led"></i>{status}</em></div><span class="line r"></span></div>')
	return _upsert_block(f"WB Divider {title}", html, _tpl("divider.css"))


def banner_block():
	html = ('<div class="wbb"><div><h2>Vyavantra Weighbridge</h2><p>Weighment, billing, payments, masters and reports</p></div>'
			'<div class="acts"><button class="b solid" data-new="Weighment Slip">+ New Weighment Slip</button>'
			'<button class="b" data-go="Workspaces/Dashboard">Open Dashboard</button></div></div>')
	return _upsert_block("WB Banner Weighbridge", html, _tpl("banner.css"), _tpl("banner.js"))


def restyle_headers(content):
	"""The original plain headers (Diesel Management, Master Data...) take the shared divider look."""
	out = []
	for b in content:
		if b.get("type") == "header":
			title = frappe.utils.strip_html(b["data"].get("text", "")).strip()
			if title in DIVIDERS:
				b = {"id": b["id"], "type": "custom_block", "data": {"custom_block_name": divider_block(title), "col": 12}}
		out.append(b)
	return out


def sync_custom_blocks(ws, content=None):
	"""Keep the workspace's custom block rows equal to the custom_block entries in its content."""
	content = content if content is not None else json.loads(ws.content or "[]")
	names = []
	for b in content:
		n = b.get("data", {}).get("custom_block_name")
		if b.get("type") == "custom_block" and n and n not in names:
			names.append(n)
	have = {r.custom_block_name for r in ws.custom_blocks}
	ws.custom_blocks = [r for r in ws.custom_blocks if r.custom_block_name in names or not r.custom_block_name.startswith("WB ")]
	for n in names:
		if n not in {r.custom_block_name for r in ws.custom_blocks}:
			ws.append("custom_blocks", {"custom_block_name": n, "label": n})
