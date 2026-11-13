import frappe

from vyavantra_weighbridge.setup import ensure_roles


def execute():
	"""Rename the old Chit Boy role; its legacy Web Form is removed during the Desk cutover."""
	if frappe.db.exists("Role", "Chit Boy"):
		frappe.rename_doc("Role", "Chit Boy", "Slip Boy", force=True, merge=bool(frappe.db.exists("Role", "Slip Boy")))
	ensure_roles()
	if frappe.db.exists("Web Form", "chit-boy"):
		frappe.delete_doc("Web Form", "chit-boy", force=True, ignore_permissions=True)
	frappe.db.commit()
