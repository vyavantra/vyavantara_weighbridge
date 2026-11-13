# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

"""Roles, default shifts, print formats and seed masters for the weighbridge module.

Everything here is idempotent. The workspace, number cards and dashboard charts are NOT built here: they are
exported into the app (workspace/, number_card/, dashboard_chart/) and synced by `bench migrate`.
"""

import frappe

ROLES = ("Weighbridge Manager", "Weighbridge User", "Slip Boy")
SHIFTS = (
	("Shift 1", "04:00:00", "12:00:00"),
	("Shift 2", "12:00:00", "20:00:00"),
	("Shift 3", "20:00:00", "04:00:00"),
)


def after_install():
	ensure_roles()
	after_migrate_setup()


def ensure_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


def after_migrate_setup():
	ensure_roles()
	create_shifts()
	ensure_bank_fields()
	ensure_discount_fields()
	seed_varieties()
	seed_delivery_types()
	set_default_print_formats()
	frappe.db.commit()


# A standard DocType cannot carry `default_print_format` in its JSON (DocType.validate throws), so it is
# applied as a Property Setter, which is what Customize Form creates.
DEFAULT_PRINT_FORMATS = (
	("Weighment Slip", "Weighment Slip Print"),
	("General Weighment Slip", "General Weighment Slip Print"),
)


def set_default_print_formats():
	for doctype, print_format in DEFAULT_PRINT_FORMATS:
		if not (frappe.db.exists("DocType", doctype) and frappe.db.exists("Print Format", print_format)):
			continue
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"doctype_or_field": "DocType",
				"property": "default_print_format",
				"value": print_format,
				"property_type": "Data",
			}
		)


def create_shifts():
	if not frappe.db.exists("DocType", "Weighbridge Shift"):
		return
	for name, start, end in SHIFTS:
		if not frappe.db.exists("Weighbridge Shift", name):
			frappe.get_doc(
				{"doctype": "Weighbridge Shift", "shift_name": name, "start_time": start, "end_time": end}
			).insert(ignore_permissions=True)


DELIVERY_TYPES = ("Farm Delivery", "Gate Cane", "Harvesting Machine")
VARIETIES = ("86032", "265", "10001", "15012", "671", "9805", "8005", "419", "0265")


def ensure_bank_fields():
	"""IFSC code and address on the core Bank doctype (the weighbridge uses Bank, not its own bank master)."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Bank": [
		{"fieldname": "ifsc_code", "fieldtype": "Data", "label": "IFSC Code", "insert_after": "bank_name",
		 "in_list_view": 1},
		{"fieldname": "bank_address", "fieldtype": "Small Text", "label": "Address", "insert_after": "ifsc_code"},
	]}, ignore_validate=True)


# Line discount the way a factory reads a bill: Qty and Rate stay exactly as typed, the discount only
# lowers the line Amount. ERPNext's own Discount (%) / Discount Amount work the other way round, they
# recompute Rate from Price List Rate, which hides the rate the buyer agreed on.
DISCOUNT_FIELDS = [
	{
		"fieldname": "vw_discount_type",
		"fieldtype": "Select",
		"label": "Discount Type",
		"options": "\nPercentage\nAmount",
		"insert_after": "rate",
		"in_list_view": 1,
		"columns": 1,
		"translatable": 0,
	},
	{
		"fieldname": "vw_discount_value",
		"fieldtype": "Float",
		"label": "Discount",
		"insert_after": "vw_discount_type",
		"depends_on": "eval:doc.vw_discount_type",
		"mandatory_depends_on": "eval:doc.vw_discount_type",
		"in_list_view": 1,
		"columns": 1,
		"description": "Percentage of the line, or a flat amount off the line",
	},
	{
		"fieldname": "vw_discount_amount",
		"fieldtype": "Currency",
		"label": "Discount Amount",
		"insert_after": "vw_discount_value",
		"depends_on": "eval:doc.vw_discount_type",
		"read_only": 1,
		"no_copy": 1,
		"description": "What the discount took off this line",
	},
]


def ensure_discount_fields():
	"""Discount Type / Discount on the invoice item rows of both Sales and Purchase Invoice."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{dt: DISCOUNT_FIELDS for dt in ("Sales Invoice Item", "Purchase Invoice Item")},
		ignore_validate=True,
	)


def seed_varieties():
	if not frappe.db.exists("DocType", "Cane Variety"):
		return
	for v in VARIETIES:
		if not frappe.db.exists("Cane Variety", v):
			frappe.get_doc({"doctype": "Cane Variety", "variety_name": v}).insert(ignore_permissions=True)


def seed_delivery_types():
	if not frappe.db.exists("DocType", "Delivery Type"):
		return
	for d in DELIVERY_TYPES:
		if not frappe.db.exists("Delivery Type", d):
			frappe.get_doc({"doctype": "Delivery Type", "delivery_type_name": d}).insert(ignore_permissions=True)
