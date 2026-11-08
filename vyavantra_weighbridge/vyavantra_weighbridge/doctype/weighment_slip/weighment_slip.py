# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_time, getdate, nowtime

from vyavantra_weighbridge.indicator import read_indicator_weight

BILL_LINKS = ("farmer_bill", "tractor_bill", "todani_bill", "agent_bill")


class WeighmentSlip(Document):
	def before_insert(self):
		self.serial_no = (
			cint(
				frappe.db.sql(
					"select max(serial_no) from `tabWeighment Slip` where slip_date = %s", self.slip_date
				)[0][0]
			)
			+ 1
		)

	def validate(self):
		if not self.slip_time:
			self.slip_time = nowtime()
		self.set_vehicle_defaults()
		if self.docstatus == 0:
			self.shift = get_shift_for_time(self.slip_time)
			self.set_route_details()
			self.fetch_rates()
		self.validate_contractors()
		self.calculate_weights()
		if self.amended_from and not self.correction_reason:
			frappe.throw(_("Please enter the reason for the re-weighing / correction"))

	# --- defaults ---------------------------------------------------------------------
	def set_vehicle_defaults(self):
		if self.vehicle:
			# the number itself, kept on the slip for registers and bills (the link holds the record id)
			self.vehicle_no = frappe.db.get_value("Tractor Number", self.vehicle, "tractor_number")
			if not self.transport_contractor:
				self.transport_contractor = get_tractor_contractor(self.vehicle)
		if self.farmer and not self.village:
			self.village = frappe.db.get_value("Cane Supplier", self.farmer, "village")

	def set_route_details(self):
		routes = get_village_route_rows(self.village)
		if self.route:
			if not self.village:
				frappe.throw(_("Select the member (village) before the route"))
			row = routes.get(self.route)
			if not row:
				frappe.throw(_("Route {0} is not defined for village {1}").format(self.route, self.village))
			self.distance = flt(row.distance_km)
			self.transport_rate = flt(row.transport_rate)
		elif routes:
			frappe.throw(_("Please select a route for village {0}").format(self.village))
		else:
			# village without routes: no distance and no route rate
			self.distance = 0
			self.transport_rate = 0

	def fetch_rates(self):
		rates = get_rate_master_rates(self.slip_date, self.delivery_type)
		if not rates:
			frappe.throw(
				_("No Cane Rate Master has a rate for Delivery Type {0} on {1}").format(
					frappe.bold(self.delivery_type), frappe.format(getdate(self.slip_date), "Date")
				)
			)
		self.cane_rate = rates["cane_rate"]
		self.todani_rate = rates["todani_rate"]
		self.farakt_rate = rates["farakt_rate"]

	def validate_contractors(self):
		for field, allowed in (
			("transport_contractor", ("Tractor", "Both")),
			("cutting_contractor", ("Cutting Contractor", "Both")),
		):
			c = self.get(field)
			if c:
				ctype = frappe.db.get_value("Contractor Master", c, "contractor_type")
				if ctype not in allowed:
					frappe.throw(
						_("{0} must be a {1} contractor").format(self.meta.get_label(field), _(" / ").join(allowed))
					)

	def calculate_weights(self):
		"""Cane Weight = Loaded - Empty. Net Cane Weight = Cane Weight - Binding Material.
		Other Deduction (Kg) = Other Deduction % of the Net Cane Weight. Net Weight = Net Cane Weight - Other Deduction,
		the quantity that is billed. Every figure is recalculated here, whatever the client sent."""
		loaded, empty, binding = flt(self.gross_weight), flt(self.tare_weight), flt(self.mat_weight)
		percent = flt(self.other_deduction_percent)
		if loaded < 0 or empty < 0 or binding < 0:
			frappe.throw(_("Weights cannot be negative"))
		if not 0 <= percent <= 100:
			frappe.throw(_("Other Deduction % must be between 0 and 100"))
		if loaded and empty and loaded <= empty:
			frappe.throw(_("Loaded Vehicle Weight must be greater than Empty Vehicle Weight"))
		# the formula always applies: with the empty weight still 0 the figures simply follow the loaded weight
		self.cane_weight = flt(loaded - empty, 2) if loaded else 0
		if binding > self.cane_weight:
			frappe.throw(_("Binding Material Weight cannot be more than the Cane Weight"))
		self.net_after_binding = flt(self.cane_weight - binding, 2)
		self.other_deduction = flt(self.net_after_binding * percent / 100, 2)
		self.net_cane_weight = flt(self.net_after_binding - self.other_deduction, 2)

	# --- submit / cancel --------------------------------------------------------------
	def before_submit(self):
		if not flt(self.tare_weight):
			frappe.throw(_("Empty Vehicle Weight is not taken yet"))
		if flt(self.net_cane_weight) <= 0:
			frappe.throw(_("Net Weight must be greater than zero"))

	def on_cancel(self):
		billed = [self.get(f) for f in BILL_LINKS if self.get(f)]
		if billed:
			frappe.throw(_("Weighment Slip is already billed in {0}. Cancel the bill first.").format(", ".join(billed)))


@frappe.whitelist()
def get_tractor_contractor(tractor):
	"""The Tractor contractor that owns this Tractor Number, when exactly one enabled contractor does."""
	if not tractor:
		return None
	owners = frappe.db.sql(
		"""select distinct c.name from `tabContractor Master` c join `tabContractor Tractor` t
		on t.parent = c.name and t.parenttype = 'Contractor Master'
		where t.tractor_number = %s and c.contractor_type in ('Tractor', 'Both') and c.disabled = 0""",
		tractor,
	)
	return owners[0][0] if len(owners) == 1 else None


def get_village_route_rows(village):
	"""{route name: Village Route row} for a village."""
	if not village:
		return {}
	return {r.route: r for r in frappe.get_cached_doc("Village Master", village).routes}


def get_rate_master_rates(slip_date, delivery_type):
	"""Cane / Todani / Farak rate of `delivery_type` in the Cane Rate Master whose Effective From - To range
	contains `slip_date`. None when no such master has a row for that Delivery Type."""
	if not (slip_date and delivery_type):
		return None
	row = frappe.db.sql(
		"""select r.cane_rate, r.todani_rate, r.farak_rate
		from `tabCane Rate Master` m join `tabCane Rate Delivery Type` r
			on r.parent = m.name and r.parenttype = 'Cane Rate Master'
		where m.disabled = 0 and r.delivery_type = %(t)s
			and m.effective_from <= %(d)s and (m.effective_to is null or m.effective_to >= %(d)s)
		order by m.effective_from desc, m.creation desc limit 1""",
		{"d": getdate(slip_date), "t": delivery_type},
		as_dict=True,
	)
	if not row:
		return None
	return {
		"cane_rate": flt(row[0].cane_rate),
		"todani_rate": flt(row[0].todani_rate),
		"farakt_rate": flt(row[0].farak_rate),
	}


@frappe.whitelist()
def get_cane_rates(slip_date=None, delivery_type=None):
	"""Rates shown on the slip as soon as the Delivery Type / date is chosen. {} when the master has no rate for them."""
	frappe.has_permission("Weighment Slip", "read", throw=True)
	return get_rate_master_rates(slip_date, delivery_type) or {}


@frappe.whitelist()
def get_village_routes(village):
	"""Routes of a village with their distance and rate, for the route picker on the slip."""
	frappe.has_permission("Village Master", "read", doc=village, throw=True)
	return [
		{"route": r.route, "distance_km": flt(r.distance_km), "transport_rate": flt(r.transport_rate)}
		for r in get_village_route_rows(village).values()
	]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def route_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link search for the slip's Route field: only the routes defined for the member's village.

	The village's own Village Route rows are the source, so a route that is not set up for the village
	can never be picked.
	"""
	filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
	village = (filters or {}).get("village")
	if not village:
		return []
	txt = (txt or "").strip().lower()
	rows = [
		(r.route, _("{0} Km  |  Rs {1} per Ton").format(f"{flt(r.distance_km):g}", f"{flt(r.transport_rate):g}"))
		for r in get_village_route_rows(village).values()
		if not txt or txt in r.route.lower()
	]
	return rows[cint(start) : cint(start) + cint(page_len)]


@frappe.whitelist()
def get_indicator_weight():
	"""Read the current weight (Kg) from the weighbridge indicator configured in Weighbridge Settings."""
	frappe.has_permission("Weighment Slip", "create", throw=True)
	return read_indicator_weight()


def get_shift_for_time(slip_time):
	"""Name of the enabled Weighbridge Shift that contains `slip_time`, or None.

	A shift that crosses midnight (start later than end, e.g. 20:00-04:00) matches both late evening
	and early morning. The end time itself belongs to the next shift.
	"""
	if not slip_time:
		return None
	t = get_time(slip_time)
	for sh in frappe.get_all(
		"Weighbridge Shift",
		filters={"disabled": 0},
		fields=["name", "start_time", "end_time"],
		order_by="start_time",
	):
		start, end = get_time(sh.start_time), get_time(sh.end_time)
		if (start <= t < end) if start < end else (t >= start or t < end):
			return sh.name
	return None


@frappe.whitelist()
def get_shift(slip_time=None):
	"""Shift for the time typed on the slip, so the form can fill it as soon as the time changes."""
	frappe.has_permission("Weighment Slip", "read", throw=True)
	return get_shift_for_time(slip_time)
