import frappe


def execute():
	"""Rows of bills made before Gross Quantity existed take it from their own Cane Weight."""
	frappe.reload_doc("vyavantra_weighbridge", "doctype", "farmer_bill_slip")
	frappe.db.sql(
		"""update `tabFarmer Bill Slip`
		set gross_quantity = round(ifnull(cane_weight, 0) / 1000, 3)
		where ifnull(gross_quantity, 0) = 0 and ifnull(cane_weight, 0) != 0"""
	)
