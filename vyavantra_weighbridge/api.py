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
