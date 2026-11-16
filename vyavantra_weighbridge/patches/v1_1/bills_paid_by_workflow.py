"""Farmer and Tractor Contractor Bills are now saved as Unpaid and submitted by Pay.

A bill that was approved (submitted) but never paid goes back to an editable Unpaid bill and lets go of its
slips, exactly as a saved bill holds none until it is paid. A bill with a payment stays submitted, as Paid.
"""

import frappe

BILLS = {
	"Farmer Bill": ("Farmer Bill Slip", ("farmer_bill",)),
	"Tractor Contractor Bill": ("Tractor Bill Slip", ("tractor_bill",)),
}


def execute():
	for doctype in ("farmer_bill", "tractor_contractor_bill", "contractor_master", "weighbridge_settings"):
		frappe.reload_doc("vyavantra_weighbridge", "doctype", doctype)
	settings = frappe.get_doc("Weighbridge Settings")

	for doctype, (child, flags) in BILLS.items():
		for bill in frappe.get_all(doctype, filters={"docstatus": 1}, fields=["name", "paid_amount", "payment_status"]):
			if bill.paid_amount or bill.payment_status in ("Paid", "Partly Paid"):
				frappe.db.set_value(doctype, bill.name, "workflow_status", "Paid", update_modified=False)
				continue
			frappe.db.sql(f"update `tab{doctype}` set docstatus = 0 where name = %s", bill.name)
			frappe.db.sql(f"update `tab{child}` set docstatus = 0 where parent = %s and parenttype = %s", (bill.name, doctype))
			for flag in flags:
				frappe.db.sql(f"update `tabWeighment Slip` set `{flag}` = null where `{flag}` = %s", bill.name)
			if doctype == "Tractor Contractor Bill":
				frappe.db.sql("update `tabDiesel Issue Entry` set tractor_bill = null where tractor_bill = %s", bill.name)
			if doctype == "Farmer Bill":
				frappe.db.set_value(doctype, bill.name, {"approval_status": "Draft", "payment_status": "Draft"},
				                    update_modified=False)

		frappe.db.sql(f"update `tab{doctype}` set workflow_status = 'Unpaid' where docstatus = 0")
		frappe.db.sql(f"update `tab{doctype}` set workflow_status = 'Cancelled' where docstatus = 2")
		# unpaid bills start from the accounts of Weighbridge Settings; each can be changed on the bill
		defaults = {"company": settings.company, "paid_from": settings.bank_account}
		if doctype == "Farmer Bill":
			defaults["paid_to"] = settings.cane_purchase_account
		for field, value in defaults.items():
			if value:
				frappe.db.sql(
					f"update `tab{doctype}` set `{field}` = %s where docstatus = 0 and ifnull(`{field}`, '') = ''", value
				)
