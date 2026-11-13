import frappe

# Vehicle numbers are written in capitals. Records typed before TractorNumber.validate() enforced it
# still hold whatever case the operator used, which makes the same vehicle look like two.


def execute():
	if not frappe.db.exists("DocType", "Tractor Number"):
		return

	for name, number in frappe.get_all("Tractor Number", fields=["name", "tractor_number"], as_list=True):
		if not number:
			continue
		upper = number.strip().upper()
		if upper != number:
			frappe.db.set_value("Tractor Number", name, "tractor_number", upper, update_modified=False)

	# the slip keeps a copy of the number it was weighed with
	if frappe.db.has_column("Weighment Slip", "vehicle_no"):
		frappe.db.sql("update `tabWeighment Slip` set vehicle_no = upper(trim(vehicle_no)) where vehicle_no is not null")

	frappe.db.commit()
