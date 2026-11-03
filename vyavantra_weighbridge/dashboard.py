# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

"""Data for the custom Dashboard workspace (one whitelisted call, a handful of grouped queries)."""

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

SLIP = "`tabWeighment Slip`"
BILLS = (("farmer", "Farmer Bill"), ("tractor", "Tractor Contractor Bill"),
		 ("todani", "Todani Contractor Bill"), ("agent", "Agent Bill"))


def season_start(today):
	today = getdate(today)
	year = today.year if today.month >= 10 else today.year - 1
	return getdate(f"{year}-10-01")


def _can(doctype):
	return frappe.has_permission(doctype, "read")


def _hm(t):
	if not t:
		return ""
	secs = int(t.total_seconds()) if hasattr(t, "total_seconds") else 0
	return f"{secs // 3600 % 24:02d}:{secs // 60 % 60:02d}"


def _t(kg):
	return round(flt(kg) / 1000.0, 3)


@frappe.whitelist()
def get_dashboard_data():
	frappe.has_permission("Weighment Slip", "read", throw=True)
	today = getdate(nowdate())
	start = season_start(today)
	trend_from = add_days(today, -29)
	ok = "docstatus = 1 and net_cane_weight > 0"

	day = frappe.db.sql(f"""select count(*) trips, coalesce(sum(net_cane_weight), 0) kg
		from {SLIP} where {ok} and slip_date = %s""", today, as_dict=True)[0]
	yday = frappe.db.sql(f"""select coalesce(sum(net_cane_weight), 0) kg
		from {SLIP} where {ok} and slip_date = %s""", add_days(today, -1))[0][0]
	season = frappe.db.sql(f"""select count(*) trips, coalesce(sum(net_cane_weight), 0) kg
		from {SLIP} where {ok} and slip_date >= %s""", start, as_dict=True)[0]
	cancelled = frappe.db.count("Weighment Slip", {"docstatus": 2, "slip_date": [">=", start]})

	rows = frappe.db.sql(f"""select slip_date d, sum(net_cane_weight) kg from {SLIP}
		where {ok} and slip_date between %s and %s group by slip_date""", (trend_from, today), as_dict=True)
	by_day = {getdate(r.d): r.kg for r in rows}
	trend = [{"date": str(add_days(trend_from, i)), "tons": _t(by_day.get(getdate(add_days(trend_from, i)), 0))}
			 for i in range(30)]

	shifts = frappe.db.sql(f"""select coalesce(shift, 'No shift') label, count(*) trips, sum(net_cane_weight) kg
		from {SLIP} where {ok} and slip_date >= %s group by shift order by shift""", start, as_dict=True)

	villages = frappe.db.sql(f"""select coalesce(village, 'Unknown') label, sum(net_cane_weight) kg from {SLIP}
		where {ok} and slip_date >= %s group by village order by kg desc limit 8""", start, as_dict=True)

	delivery = frappe.db.sql(f"""select coalesce(delivery_type, 'Other') label, sum(net_cane_weight) kg from {SLIP}
		where {ok} and slip_date >= %s group by delivery_type order by kg desc""", start, as_dict=True)

	recent = frappe.db.sql(f"""select name, slip_date, slip_time, vehicle, farmer_name, village, net_cane_weight
		from {SLIP} where {ok} order by slip_date desc, slip_time desc, creation desc limit 8""", as_dict=True)

	out = {}
	for key, dt in BILLS:
		out[key] = flt(frappe.db.sql(f"select coalesce(sum(outstanding_amount), 0) from `tab{dt}` where docstatus = 1")[0][0]) \
			if _can(dt) else 0
	pending = frappe.db.count("Weighbridge Payment", {"docstatus": 0, "approval_status": "Pending"}) \
		if _can("Weighbridge Payment") else 0
	paid = flt(frappe.db.sql("""select coalesce(sum(amount), 0) from `tabWeighbridge Payment`
		where docstatus = 1 and payment_date = %s""", today)[0][0]) if _can("Weighbridge Payment") else 0

	s = frappe.get_cached_doc("Weighbridge Settings")
	return {
		"company": s.report_company_name or "", "today": str(today), "season_start": str(start),
		"kpi": {
			"today_tons": _t(day.kg), "today_trips": day.trips, "yesterday_tons": _t(yday),
			"season_tons": _t(season.kg), "season_trips": season.trips, "cancelled": cancelled,
			"pending_payments": pending, "paid_today": paid,
		},
		"outstanding": out,
		"trend": trend,
		"shifts": [{"label": r.label, "trips": r.trips, "tons": _t(r.kg)} for r in shifts],
		"villages": [{"label": r.label, "tons": _t(r.kg)} for r in villages],
		"delivery": [{"label": r.label, "tons": _t(r.kg)} for r in delivery],
		"recent": [{"name": r.name, "date": str(r.slip_date), "time": _hm(r.slip_time), "vehicle": r.vehicle,
					"party": r.farmer_name, "village": r.village, "tons": _t(r.net_cane_weight)} for r in recent],
	}
