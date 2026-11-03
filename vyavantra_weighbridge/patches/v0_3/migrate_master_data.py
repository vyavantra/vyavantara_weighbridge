import frappe
from frappe.utils import flt

from vyavantra_weighbridge.setup import after_migrate_setup, ensure_bank_fields, seed_varieties


def _col(doctype, column):
	return frappe.db.has_column(doctype, column)


def execute():
	ensure_bank_fields()
	seed_varieties()

	# renamed fields: copy the old column into the new one
	if _col("Cane Supplier", "member_no"):
		frappe.db.sql("update `tabCane Supplier` set cane_supplier_no = member_no where ifnull(cane_supplier_no, '') = ''")
	if _col("Cane Rate Master", "farakt_rate"):
		frappe.db.sql("update `tabCane Rate Master` set farak_rate = farakt_rate where ifnull(farak_rate, 0) = 0")
	frappe.db.sql("update `tabContractor Master` set contractor_type = 'Cutting Contractor' where contractor_type = 'Cutting'")

	# core Bank in place of Weighbridge Bank
	if frappe.db.table_exists("Weighbridge Bank"):
		for b in frappe.db.sql("select * from `tabWeighbridge Bank`", as_dict=True):
			if not frappe.db.exists("Bank", b.bank_name):
				doc = frappe.get_doc({"doctype": "Bank", "bank_name": b.bank_name, "ifsc_code": b.get("ifsc_code"),
									  "bank_address": b.get("address")})
				doc.insert(ignore_permissions=True)
		if frappe.db.exists("DocType", "Weighbridge Bank"):
			frappe.delete_doc("DocType", "Weighbridge Bank", force=True, ignore_missing=True)
		frappe.db.sql_ddl("drop table if exists `tabWeighbridge Bank`")

	# village: district / taluka / distance masters from the free-text values
	villages = frappe.db.sql("select * from `tabVillage Master`", as_dict=True)
	for v in villages:
		if v.district and not frappe.db.exists("District Master", v.district):
			frappe.get_doc({"doctype": "District Master", "district_name": v.district}).insert(ignore_permissions=True)
	for v in villages:
		if v.taluka and not frappe.db.exists("Taluka Master", v.taluka):
			frappe.get_doc({"doctype": "Taluka Master", "taluka_name": v.taluka,
							"district": v.district or "Unknown"}).insert(ignore_permissions=True) if v.district else None
		if _col("Village Master", "distance") and flt(v.get("distance")) > 0:
			label = f"{flt(v.distance):g} Km"
			if not frappe.db.exists("Distance Master", label):
				frappe.get_doc({"doctype": "Distance Master", "distance_km": v.distance,
								"transport_rate": flt(v.transport_rate)}).insert(ignore_permissions=True)
			frappe.db.set_value("Village Master", v.name, "distance_master", label, update_modified=False)

	# varieties used on existing slips
	for (name,) in frappe.db.sql("select distinct variety from `tabWeighment Slip` where ifnull(variety, '') != ''"):
		if not frappe.db.exists("Cane Variety", name):
			frappe.get_doc({"doctype": "Cane Variety", "variety_name": name}).insert(ignore_permissions=True)

	# season is now a Fiscal Year link
	from erpnext.accounts.utils import get_fiscal_year

	for r in frappe.get_all("Cane Rate Master", fields=["name", "season", "effective_from"]):
		if not frappe.db.exists("Fiscal Year", r.season):
			try:
				fy = get_fiscal_year(r.effective_from, as_dict=True).name
				frappe.db.set_value("Cane Rate Master", r.name, "season", fy, update_modified=False)
			except Exception:
				pass

	after_migrate_setup()
