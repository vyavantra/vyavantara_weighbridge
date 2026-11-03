# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from vyavantra_weighbridge.report_utils import check_access, fmt_date, tons


def execute(filters=None):
	check_access()
	filters = frappe._dict(filters or {})
	from_date, to_date = getdate(filters.from_date or nowdate()), getdate(filters.to_date or nowdate())
	if from_date > to_date:
		frappe.throw(_("From Date cannot be after To Date"))
	rows = frappe.db.sql(
		"""select s.slip_date, s.name slip_no, s.farmer_name, v.village_name village, s.variety, s.vehicle_no vehicle,
			cc.contractor_name todani_contractor, tc.contractor_name transporter, s.net_cane_weight
		from `tabWeighment Slip` s
		left join `tabVillage Master` v on v.name = s.village
		left join `tabContractor Master` cc on cc.name = s.cutting_contractor
		left join `tabContractor Master` tc on tc.name = s.transport_contractor
		where s.docstatus = 1 and s.net_cane_weight > 0 and s.slip_date between %s and %s
		order by s.slip_date, s.slip_time, s.name""",
		(from_date, to_date), as_dict=True,
	)
	columns = [
		{"fieldname": "sr_no", "label": _("Sr No"), "fieldtype": "Int", "width": 60},
		{"fieldname": "farmer_name", "label": _("Farmer Name"), "fieldtype": "Data", "width": 170},
		{"fieldname": "village", "label": _("Village"), "fieldtype": "Data", "width": 150},
		{"fieldname": "variety", "label": _("Cane Variety"), "fieldtype": "Data", "width": 90},
		{"fieldname": "vehicle", "label": _("Veh No"), "fieldtype": "Data", "width": 110},
		{"fieldname": "slip_no", "label": _("Slip No"), "fieldtype": "Data", "width": 120},
		{"fieldname": "todani_contractor", "label": _("Tod Cont Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "transporter", "label": _("Transporter Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "cane_weight", "label": _("Cn Wt"), "fieldtype": "Float", "precision": 3, "width": 90},
	]
	data, sr, day_total, grand, current = [], 0, 0.0, 0.0, None

	def close_day():
		if current is not None:
			data.append({"farmer_name": _("Sub Total"), "cane_weight": round(day_total, 3), "row_type": "subtotal"})

	for r in rows:
		if r.slip_date != current:
			close_day()
			current, day_total = r.slip_date, 0.0
			data.append({"farmer_name": _("For Date") + " " + fmt_date(current), "row_type": "date"})
		sr += 1
		w = tons(r.net_cane_weight)
		day_total += w
		grand += w
		data.append({"sr_no": sr, "farmer_name": r.farmer_name, "village": r.village, "variety": r.variety,
					 "vehicle": r.vehicle, "slip_no": r.slip_no, "todani_contractor": r.todani_contractor,
					 "transporter": r.transporter, "cane_weight": w, "row_type": "slip"})
	close_day()
	if rows:
		data.append({"farmer_name": _("Grand Total"), "cane_weight": round(grand, 3), "row_type": "total"})
	return columns, data
