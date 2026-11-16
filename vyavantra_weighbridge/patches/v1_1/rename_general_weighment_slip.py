"""Rename DocType "General Weighment Slip" to "Other Weight"."""

import frappe


def execute():
    if frappe.db.exists("DocType", "General Weighment Slip"):
        frappe.rename_doc("DocType", "General Weighment Slip", "Other Weight", force=True)
        frappe.db.commit()
