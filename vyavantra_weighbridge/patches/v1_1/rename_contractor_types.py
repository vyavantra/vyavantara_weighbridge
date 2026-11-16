import frappe

# The contractor types as the office names them. Tractor Contractor Bill and Todani Contractor Bill keep the
# type of their contractor as text, so they are renamed with the master.
RENAMES = {"Tractor": "Tractor Contractor", "Both": "Tractor / Cutting Contractor"}
TABLES = ("Contractor Master", "Weighment Slip", "Tractor Contractor Bill", "Todani Contractor Bill")


def execute():
	for doctype in TABLES:
		if not frappe.db.has_column(doctype, "contractor_type"):
			continue
		for old, new in RENAMES.items():
			frappe.db.sql(f"update `tab{doctype}` set contractor_type = %s where contractor_type = %s", (new, old))
