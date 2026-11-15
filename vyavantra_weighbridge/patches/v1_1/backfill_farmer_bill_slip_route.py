import frappe


def execute():
	"""Rows of bills made before the Route column existed take the route of their weighment slip."""
	frappe.reload_doc("vyavantra_weighbridge", "doctype", "farmer_bill_slip")
	frappe.db.sql(
		"""update `tabFarmer Bill Slip` row
		join `tabWeighment Slip` slip on slip.name = row.slip
		set row.route = slip.route
		where ifnull(row.route, '') = '' and ifnull(slip.route, '') != ''"""
	)
