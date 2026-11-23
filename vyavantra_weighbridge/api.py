"""Whitelisted endpoints called from the browser (public/js/*.js), and the Link field search
override (hooks.py: override_whitelisted_methods) that makes it find Marathi-named records."""

import re

import frappe
import requests


@frappe.whitelist()
def marathi_suggestions(word):
	"""Roman word -> list of Devanagari (Marathi) candidates, via Google's phonetic
	transliteration service. Called from the server (public/js/marathi_keyboard.js) because that
	endpoint sends no CORS headers, so a browser cannot fetch() it directly cross-origin; a
	server-to-server request has no such restriction. Returns [] on any error (offline, timeout,
	unexpected response), so the typing feature degrades quietly instead of breaking the field.
	"""
	word = (word or "").strip()
	if not word:
		return []
	try:
		r = requests.get(
			"https://inputtools.google.com/request",
			params={"text": word, "itc": "mr-t-i0-und", "num": 6, "cp": 0, "cs": 1, "ie": "utf-8", "oe": "utf-8"},
			timeout=3,
		)
		data = r.json()
		if data and data[0] == "SUCCESS" and data[1] and data[1][0][1]:
			return data[1][0][1]
	except Exception:
		frappe.log_error(title="Marathi transliteration failed")
	return []


@frappe.whitelist()
def marathi_search_link(
	doctype,
	txt,
	query=None,
	filters=None,
	page_length=10,
	searchfield=None,
	reference_doctype=None,
	ignore_user_permissions=False,
):
	"""Drop-in replacement for frappe.desk.search.search_link (see hooks.py).

	Our master data (Village Master, Cane Supplier, Contractor Master, ...) is stored in Marathi.
	If the plain search for what was typed finds nothing, and what was typed looks like English,
	retry the same search with each Marathi phonetic transliteration of it in turn, stopping at
	the first one that finds matches. Typing "sahaji" this way also finds "शहाजी".
	"""
	from frappe.desk.search import search_link

	kwargs = dict(
		query=query,
		filters=filters,
		page_length=page_length,
		searchfield=searchfield,
		reference_doctype=reference_doctype,
		ignore_user_permissions=ignore_user_permissions,
	)
	txt = (txt or "").strip()
	results = search_link(doctype, txt, **kwargs)
	if results or not txt or not re.search(r"[A-Za-z]", txt):
		return results

	for candidate in marathi_suggestions(txt):
		results = search_link(doctype, candidate, **kwargs)
		if results:
			return results
	return results


@frappe.whitelist()
def import_master_data(payload):
	"""One-off live-site import helper for the historical Village/Contractor/Cane Supplier data.

	Exists only because the autoincrement IDs these doctypes carry (matching the old paper
	register's VILLNO/MEMNO/contractor codes) can only be forced with `insert(set_name=...)`,
	a Python-only kwarg with no REST equivalent — frappe.client.insert always assigns the next
	sequence value instead. Running the insert here, server-side, is what makes exact IDs
	possible over the API. Safe to re-run: anything that already exists by that id is skipped,
	not overwritten.
	"""
	frappe.only_for("System Manager")
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)

	report = {"created": [], "skipped": [], "errors": []}

	def add(doctype, name, doc_fields, child_table=None, child_rows=None):
		name = str(name)
		if frappe.db.exists(doctype, name):
			report["skipped"].append([doctype, name])
			return
		try:
			fields = dict(doc_fields)
			fields["doctype"] = doctype
			if child_table is not None:
				fields[child_table] = child_rows or []
			frappe.get_doc(fields).insert(ignore_permissions=True, set_name=name)
			report["created"].append([doctype, name])
		except Exception as e:
			report["errors"].append([doctype, name, str(e)])

	for district_name in payload.get("districts", []):
		if frappe.db.exists("District Master", district_name):
			report["skipped"].append(["District Master", district_name])
			continue
		try:
			frappe.get_doc({
				"doctype": "District Master", "district_name": district_name, "state": "Maharashtra",
			}).insert(ignore_permissions=True)
			report["created"].append(["District Master", district_name])
		except Exception as e:
			report["errors"].append(["District Master", district_name, str(e)])

	for t in payload.get("talukas", []):
		if frappe.db.exists("Taluka Master", t["name"]):
			report["skipped"].append(["Taluka Master", t["name"]])
			continue
		try:
			frappe.get_doc({
				"doctype": "Taluka Master", "taluka_name": t["name"], "district": t["district"],
			}).insert(ignore_permissions=True)
			report["created"].append(["Taluka Master", t["name"]])
		except Exception as e:
			report["errors"].append(["Taluka Master", t["name"], str(e)])

	routes_by_village = {}
	for r in payload.get("routes", []):
		routes_by_village.setdefault(str(r["parent"]), []).append(r)

	for v in payload.get("villages", []):
		rows = [
			{"route": r["route"], "distance_km": r.get("distance_km") or 0, "transport_rate": r.get("transport_rate") or 0}
			for r in routes_by_village.get(str(v["name"]), [])
		]
		add("Village Master", v["name"], {
			"village_name": v["village_name"], "taluka": v["taluka"], "district": v["district"],
		}, child_table="routes", child_rows=rows)

	for t in payload.get("tractor_numbers", []):
		add("Tractor Number", t["name"], {"tractor_number": t["tractor_number"]})

	tractors_by_contractor = {}
	for ct in payload.get("contractor_tractors", []):
		tractors_by_contractor.setdefault(str(ct["parent"]), []).append(ct["tractor_number"])

	for c in payload.get("contractors", []):
		rows = [{"tractor_number": tn} for tn in tractors_by_contractor.get(str(c["name"]), [])]
		add("Contractor Master", c["name"], {
			"contractor_name": c["contractor_name"], "contractor_type": c["contractor_type"],
			"old_contractor_code": c.get("old_contractor_code"), "village": c.get("village"),
			"phone": c.get("phone"), "disabled": c.get("disabled") or 0,
			"bank": c.get("bank"), "bank_account_no": c.get("bank_account_no"), "ifsc_code": c.get("ifsc_code"),
		}, child_table="tractors", child_rows=rows)

	for cs in payload.get("cane_suppliers", []):
		add("Cane Supplier", cs["name"], {
			"farmer_name": cs["farmer_name"], "village": cs.get("village"),
			"phone": cs.get("phone"), "address": cs.get("address"), "disabled": cs.get("disabled") or 0,
			"bank": cs.get("bank"), "bank_account_no": cs.get("bank_account_no"),
			"ifsc_code": cs.get("ifsc_code"), "aadhaar_number": cs.get("aadhaar_number"),
		})

	frappe.db.commit()
	return report


@frappe.whitelist()
def fix_tractor_number_series():
	"""Re-sync Tractor Number's naming series after import_master_data forces explicit ids.

	Tractor Number is named by series (TRNO-.YYYY.-.#####), not autoincrement, but the same
	problem applies: a forced `insert(set_name=...)` never touches the counter the series reads
	from (the separate `tabSeries` table), so the next real "+ New" can collide with an id the
	import already used. Only doctype this import forced an explicit *series* name on, so it's
	the only one besides the 4 autoincrement ones that needs this.
	"""
	frappe.only_for("System Manager")
	from frappe.model.naming import NamingSeries

	meta = frappe.get_meta("Tractor Number")
	series_pattern = meta.autoname.split("naming_series:", 1)[-1]
	ns = NamingSeries(series_pattern)
	prefix = ns.get_prefix()
	max_suffix = frappe.db.sql(
		"""select max(cast(substring(name, %s) as unsigned))
		from `tabTractor Number` where name like %s""",
		(len(prefix) + 1, prefix + "%"),
	)[0][0] or 0
	ns.update_counter(int(max_suffix))
	frappe.db.commit()
	return {"prefix": prefix, "set_to": int(max_suffix)}


@frappe.whitelist()
def fix_autoincrement_sequences():
	"""Re-sync the autoincrement sequence after import_master_data forces explicit IDs.

	Autoincrement naming uses a separate MariaDB SEQUENCE object, not the table's own data — an
	explicit `insert(set_name=...)` never advances it. Left alone, the next real "+ New" in the
	UI collides with an id import_master_data already used. Run this once, right after an import.

	On a site where every row for a doctype was ever created via a forced `set_name` insert (no
	normal "+ New" has happened yet), the sequence object itself may never have been created -
	`create_sequence(check_not_exists=True)` mirrors what DocType sync does, so it's safe either way.
	"""
	frappe.only_for("System Manager")
	result = {}
	for doctype in ("Cane Supplier", "Contractor Master", "Village Master", "Cane Agent"):
		max_id = frappe.db.sql(f"select max(name) from `tab{doctype}`")[0][0] or 0
		frappe.db.create_sequence(doctype, check_not_exists=True)
		frappe.db.set_next_sequence_val(doctype, int(max_id), is_val_used=True)
		result[doctype] = int(max_id)
	frappe.db.commit()
	return result


@frappe.whitelist()
def add_village_routes(payload):
	"""Create Route Master records and attach them to Village Master's routes child table.

	import_master_data's embedded "routes" rows point at Route Master by name but never created
	the Route Master records themselves, so those links are currently dangling on the live site.
	This both backfills missing Route Master records and adds new village<->route associations,
	skipping any pair a village already has (by exact route name) so it's safe to re-run.

	payload: {"route_masters": ["route name", ...], "village_routes": [{"village": "13", "route": "..."}]}
	"""
	frappe.only_for("System Manager")
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)

	report = {"routes_created": [], "routes_skipped": [], "added": [], "skipped": [], "errors": []}

	for route_name in payload.get("route_masters", []):
		if frappe.db.exists("Route Master", route_name):
			report["routes_skipped"].append(route_name)
			continue
		frappe.get_doc({"doctype": "Route Master", "route_name": route_name}).insert(ignore_permissions=True)
		report["routes_created"].append(route_name)

	for vr in payload.get("village_routes", []):
		village = str(vr["village"])
		route = vr["route"]
		try:
			doc = frappe.get_doc("Village Master", village)
			if any(row.route == route for row in doc.routes):
				report["skipped"].append([village, route])
				continue
			doc.append("routes", {"route": route, "distance_km": vr.get("distance_km") or 0, "transport_rate": vr.get("transport_rate") or 0})
			doc.save(ignore_permissions=True)
			report["added"].append([village, route])
		except Exception as e:
			report["errors"].append([village, route, str(e)])

	frappe.db.commit()
	return report


BILL_DOCTYPES = ("Farmer Bill", "Tractor Contractor Bill", "Todani Contractor Bill", "Agent Bill")

# every doctype the workspace dashboard links to, so the page can hide what this user may not open
WORKSPACE_DOCTYPES = (
	"Weighment Slip", "Other Weight", "Diesel Issue Entry",
	"Farmer Bill", "Tractor Contractor Bill", "Todani Contractor Bill", "Agent Bill",
	"Cane Supplier", "Contractor Master", "Village Master", "Cane Agent",
)


@frappe.whitelist()
def workspace_stats():
	"""Figures for the tiles on the Vyavantra Weighbridge workspace.

	Read-only. Each doctype is skipped when the user cannot read it, so a Slip Boy sees the
	slip numbers and simply no bill count, rather than a permission error on the whole page.
	"""
	from frappe.utils import add_days, get_first_day, getdate, today

	day = today()
	# the page hides every card and link this user cannot read, so a weighbridge operator
	# simply does not see Billing instead of being sent to a permission error
	can_read = {dt: bool(frappe.has_permission(dt, "read")) for dt in WORKSPACE_DOCTYPES}
	stats = {"date": day, "can_read": can_read, "can_read_slips": can_read["Weighment Slip"]}

	if stats["can_read_slips"]:
		row = frappe.db.sql(
			"""select count(name) n, coalesce(sum(net_cane_weight), 0) kg
			from `tabWeighment Slip` where docstatus = 1 and slip_date = %s""", (day,))[0]
		stats["today_slips"], stats["today_kg"] = int(row[0]), float(row[1])

		row = frappe.db.sql(
			"""select count(name) n, coalesce(sum(net_cane_weight), 0) kg
			from `tabWeighment Slip` where docstatus = 1 and slip_date between %s and %s""",
			(get_first_day(day), day))[0]
		stats["month_slips"], stats["month_kg"] = int(row[0]), float(row[1])

		stats["open_drafts"] = frappe.db.count("Weighment Slip", {"docstatus": 0})

		# last 7 days including today, oldest first, for the sparkline.
		# both sides are keyed on the plain yyyy-mm-dd string: the query returns date objects
		# while add_days returns datetimes, and those two never compare equal.
		start = getdate(add_days(day, -6))
		by_day = {str(getdate(d)): float(kg or 0) for d, kg in frappe.db.sql(
			"""select slip_date, coalesce(sum(net_cane_weight), 0)
			from `tabWeighment Slip` where docstatus = 1 and slip_date between %s and %s
			group by slip_date""", (start, day))}
		trend = []
		for i in range(7):
			key = str(getdate(add_days(start, i)))
			trend.append({"date": key, "kg": by_day.get(key, 0.0)})
		stats["trend"] = trend

	pending = 0
	counted = []
	for dt in BILL_DOCTYPES:
		if can_read[dt]:
			pending += frappe.db.count(dt, {"docstatus": 0})
			counted.append(dt)
	stats["pending_bills"] = pending
	stats["bill_doctypes"] = counted

	return stats
