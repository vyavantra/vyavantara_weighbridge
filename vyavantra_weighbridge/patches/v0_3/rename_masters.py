import frappe

RENAMES = (("Cane Farmer", "Cane Supplier"), ("Weighbridge Contractor", "Contractor Master"))


def execute():
	"""Runs before the doctype sync, so the new doctype files update the renamed doctypes in place."""
	frappe.flags.in_patch = True
	dev = frappe.local.conf.developer_mode
	frappe.local.conf.developer_mode = 1
	for old, new in RENAMES:
		if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new):
			frappe.rename_doc("DocType", old, new, force=True)
	frappe.local.conf.developer_mode = dev
	frappe.db.commit()
