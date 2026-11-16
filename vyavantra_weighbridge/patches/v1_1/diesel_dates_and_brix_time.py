import frappe


def execute():
	for doctype in ("cane_rate_diesel_history", "cane_rate_master", "brix_entry", "tractor_bill_slip", "tractor_contractor_bill"):
		frappe.reload_doc("vyavantra_weighbridge", "doctype", doctype)

	# a master's Diesel Rate has applied since the master itself began
	frappe.db.sql(
		"update `tabCane Rate Master` set diesel_effective_date = effective_from where diesel_effective_date is null"
	)
	# existing Brix Entries get their time on the 12 hour clock
	frappe.db.sql(
		"""update `tabBrix Entry` set entry_time_12 = date_format(entry_time, '%%h:%%i %%p')
		where entry_time is not null and ifnull(entry_time_12, '') = ''"""
	)
	# diesel already on a bill row keeps the rate its bill showed
	frappe.db.sql(
		"""update `tabTractor Bill Slip` r join `tabTractor Contractor Bill` b on b.name = r.parent
		set r.diesel_rate = b.diesel_rate, r.diesel_amount = round(ifnull(r.diesel_qty, 0) * ifnull(b.diesel_rate, 0), 2)
		where ifnull(r.diesel_qty, 0) != 0 and ifnull(r.diesel_rate, 0) = 0"""
	)
