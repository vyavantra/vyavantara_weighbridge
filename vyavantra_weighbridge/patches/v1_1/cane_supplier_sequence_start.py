import frappe

# Runs after the doctype sync has turned Cane Supplier into an autoincrement doctype. Such a doctype is
# numbered from a database sequence; the sync only creates that sequence when the DocType document
# itself is saved, which a JSON sync does not always do, so it is created here when missing.
#
# A fresh sequence starts at 1, which would hand out numbers the renamed members already use, so it is
# moved past the highest existing member.


def execute():
	if frappe.db.get_value("DocType", "Cane Supplier", "autoname") != "autoincrement":
		return

	frappe.db.create_sequence("Cane Supplier", check_not_exists=True)

	highest = frappe.db.sql("select max(cast(name as unsigned)) from `tabCane Supplier`")[0][0]
	if highest:
		frappe.db.set_next_sequence_val("Cane Supplier", int(highest) + 1)

	# an autoincrement doctype keeps its name in a bigint column; the table was created back when the
	# names were strings, and a varchar column sorts 10 before 9
	current = frappe.db.sql(
		"""select data_type from information_schema.columns
		where table_schema = database() and table_name = 'tabCane Supplier' and column_name = 'name'"""
	)[0][0]
	if current.lower() != "bigint":
		frappe.db.change_column_type("Cane Supplier", "name", "bigint", nullable=False)

	frappe.db.commit()
