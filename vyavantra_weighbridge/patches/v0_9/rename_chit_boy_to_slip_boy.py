import frappe

from vyavantra_weighbridge.setup import ensure_roles


def execute():
	"""Chit Boy is now Slip Boy. Renaming the Role keeps its users and permissions; the old web form (/chit-boy)
	is replaced by /slip-boy. Runs before the doctypes are synced, because they grant permissions to Slip Boy."""
	if frappe.db.exists("Role", "Chit Boy"):
		frappe.rename_doc("Role", "Chit Boy", "Slip Boy", force=True, merge=bool(frappe.db.exists("Role", "Slip Boy")))
	ensure_roles()
	if frappe.db.exists("Web Form", "chit-boy"):
		frappe.delete_doc("Web Form", "chit-boy", force=True, ignore_permissions=True)
	frappe.db.commit()
