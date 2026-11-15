import frappe

# the accounts farmer payments are booked with, set only where the site has them and nothing is chosen yet
DEFAULTS = {
	"company": ("Company", "Sagareshwar Foods LLP"),
	"bank_account": ("Account", "926020041451936 - Axis - 926020041451936 - SFL"),
	"cane_purchase_account": ("Account", "Sugar Cane Purchase - SFL"),
}


def execute():
	for doctype in ("farmer_bill", "weighbridge_settings", "cane_supplier"):
		frappe.reload_doc("vyavantra_weighbridge", "doctype", doctype)

	# existing bills enter the workflow at the state they are already in
	frappe.db.sql(
		"""update `tabFarmer Bill`
		set workflow_status = case
			when docstatus = 0 then 'Draft'
			when docstatus = 2 then 'Cancelled'
			when payment_status = 'Paid' then 'Paid'
			else 'Unpaid' end
		where ifnull(workflow_status, '') = ''"""
	)

	for field, (doctype, name) in DEFAULTS.items():
		if not frappe.db.get_single_value("Weighbridge Settings", field) and frappe.db.exists(doctype, name):
			frappe.db.set_single_value("Weighbridge Settings", field, name)
