"""Preserve existing Farmer Bill bookings while filling new display totals and lifecycle status.

Submitted bills retain their booked quantity/rate/amount and payments. Draft bills recalculate from
their slips when next saved. Historical submitted slips can disagree with their original bill, so
do not mislabel that difference as a new weight deduction.
"""

import frappe
from frappe.utils import flt


def execute():
	for bill in frappe.get_all("Farmer Bill", fields=["name", "docstatus", "total_amount", "paid_amount"]):
		rows = frappe.get_all(
			"Farmer Bill Slip", filters={"parent": bill.name, "parenttype": "Farmer Bill"},
			fields=["name", "cane_weight", "net_weight", "quantity", "rate"],
		)
		if bill.docstatus == 1:
			for row in rows:
				booked_kg = round(flt(row.quantity) * 1000)
				if booked_kg != row.net_weight:
					frappe.db.set_value("Farmer Bill Slip", row.name, "net_weight", booked_kg, update_modified=False)
					row.net_weight = booked_kg
		total_deductions = flt(
			sum((flt(row.cane_weight) - flt(row.net_weight)) / 1000 * flt(row.rate) for row in rows), 2
		) if bill.docstatus == 0 else 0
		# Draft totals will be refreshed from their slips on the next save. Do not change existing
		# submitted totals/amounts just to fill informational fields.
		frappe.db.set_value(
			"Farmer Bill", bill.name,
			{
				"total_cane_weight": sum(flt(row.cane_weight) for row in rows) if bill.docstatus == 0 else sum(flt(row.net_weight) for row in rows),
				"total_net_weight": sum(flt(row.net_weight) for row in rows),
				"total_deductions": total_deductions,
				"approval_status": "Approved" if bill.docstatus == 1 else "Draft",
				"payment_status": (
					"Draft" if bill.docstatus == 0 else
					"Paid" if flt(bill.paid_amount) > 0 and flt(bill.paid_amount) >= flt(bill.total_amount) else
					"Unpaid"
				),
			}, update_modified=False,
		)
