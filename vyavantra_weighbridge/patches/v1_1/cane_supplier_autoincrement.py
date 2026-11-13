import frappe

# Cane Supplier used to be named Cane-Supplier-001. The office wants a plain running number, which is
# Frappe's "autoincrement" naming: the name column becomes a bigint fed by a database sequence.
#
# Frappe refuses to switch a doctype that already holds rows ("Can only change to/from Autoincrement
# naming rule when there is no data"), because the column type changes. So the existing members are
# renamed to the number inside their old name first (Cane-Supplier-007 -> 7), which rename_doc carries
# through every link (Weighment Slip.farmer, Farmer Bill.farmer). The doctype sync that follows this
# patch then finds only numeric names and can change the column type.
#
# Runs before the model sync, so the new cane_supplier.json is applied to an already-numeric table.


def execute():
	if not frappe.db.exists("DocType", "Cane Supplier"):
		return
	if frappe.db.get_value("DocType", "Cane Supplier", "autoname") == "autoincrement":
		return  # already converted

	members = frappe.get_all("Cane Supplier", pluck="name")
	taken = {name for name in members if name.isdigit()}
	next_free = max((int(n) for n in taken), default=0) + 1

	for name in sorted(members):
		if name.isdigit():
			continue

		digits = "".join(ch for ch in name if ch.isdigit())
		number = str(int(digits)) if digits else ""

		if not number or number in taken:
			number = str(next_free)
			next_free += 1

		frappe.rename_doc("Cane Supplier", name, number, force=True, show_alert=False)
		frappe.db.set_value("Cane Supplier", number, "cane_supplier_no", number, update_modified=False)
		taken.add(number)

	frappe.db.commit()
