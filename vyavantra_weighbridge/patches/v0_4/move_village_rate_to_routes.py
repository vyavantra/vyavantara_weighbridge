"""Distance and Rate moved from Village Master to the rows of its Routes table.

Runs before model sync: the old columns (Village Master.distance_master / transport_rate) are still
present at that point. Every existing route row of a village gets that village's old distance and rate.
A village that has a distance/rate but no route gets one route row named "Main Road" so the value is kept.
"""

import frappe
from frappe.utils import flt

DEFAULT_ROUTE = "Main Road"


def execute():
	if not frappe.db.table_exists("Village Route"):
		return
	has_dm = frappe.db.has_column("Village Master", "distance_master")
	has_rate = frappe.db.has_column("Village Master", "transport_rate")
	if not (has_dm and has_rate):
		return

	# add the new child columns now, so the copy below does not depend on sync order
	for column, ddl in (("distance_km", "decimal(21,9) not null default 0"), ("transport_rate", "decimal(21,9) not null default 0")):
		if not frappe.db.has_column("Village Route", column):
			frappe.db.sql_ddl(f"alter table `tabVillage Route` add column `{column}` {ddl}")

	villages = frappe.db.sql(
		"""select v.name, v.transport_rate as rate, d.distance_km
		from `tabVillage Master` v left join `tabDistance Master` d on d.name = v.distance_master
		where ifnull(d.distance_km, 0) > 0 or ifnull(v.transport_rate, 0) > 0""",
		as_dict=True,
	)
	for v in villages:
		rows = frappe.db.get_all("Village Route", filters={"parent": v.name, "parenttype": "Village Master"}, pluck="name")
		if rows:
			for name in rows:
				frappe.db.set_value(
					"Village Route", name, {"distance_km": flt(v.distance_km), "transport_rate": flt(v.rate)}, update_modified=False
				)
			continue
		if not frappe.db.exists("Route Master", DEFAULT_ROUTE):
			frappe.get_doc({"doctype": "Route Master", "route_name": DEFAULT_ROUTE}).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Village Route",
				"parent": v.name,
				"parenttype": "Village Master",
				"parentfield": "routes",
				"route": DEFAULT_ROUTE,
				"distance_km": flt(v.distance_km),
				"transport_rate": flt(v.rate),
			}
		).db_insert()
