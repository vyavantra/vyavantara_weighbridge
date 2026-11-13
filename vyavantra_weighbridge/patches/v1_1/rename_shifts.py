import frappe

# The shifts were named Shift 1/2/3; the factory calls them by the time of day. The times do not change,
# only the names, and renaming carries the existing slips along (Weighment Slip.shift links by name).
RENAMES = (
	("Shift 1", "1st Shift Morning"),
	("Shift 2", "2nd Shift Day"),
	("Shift 3", "3rd Shift Night"),
)


def execute():
	if not frappe.db.exists("DocType", "Weighbridge Shift"):
		return

	for old, new in RENAMES:
		if not frappe.db.exists("Weighbridge Shift", old):
			continue
		if frappe.db.exists("Weighbridge Shift", new):
			continue  # already renamed, or the new name was created by hand
		frappe.rename_doc("Weighbridge Shift", old, new, force=True, show_alert=False)

	frappe.db.commit()
