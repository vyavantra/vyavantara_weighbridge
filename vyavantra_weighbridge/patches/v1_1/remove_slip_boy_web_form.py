"""Slip Boy now uses the submittable Slip Boy Entry Desk DocType, not a website Web Form."""

import frappe


def execute():
	if frappe.db.exists("Web Form", "slip-boy"):
		frappe.delete_doc("Web Form", "slip-boy", force=True, ignore_permissions=True)
