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
def fix_autoincrement_sequences():
	"""Re-sync the autoincrement sequence after import_master_data forces explicit IDs.

	Autoincrement naming uses a separate MariaDB SEQUENCE object, not the table's own data — an
	explicit `insert(set_name=...)` never advances it. Left alone, the next real "+ New" in the
	UI collides with an id import_master_data already used. Run this once, right after an import.
	"""
	frappe.only_for("System Manager")
	result = {}
	for doctype in ("Cane Supplier", "Contractor Master", "Village Master", "Cane Agent"):
		max_id = frappe.db.sql(f"select max(name) from `tab{doctype}`")[0][0] or 0
		frappe.db.set_next_sequence_val(doctype, int(max_id), is_val_used=True)
		result[doctype] = int(max_id)
	frappe.db.commit()
	return result
