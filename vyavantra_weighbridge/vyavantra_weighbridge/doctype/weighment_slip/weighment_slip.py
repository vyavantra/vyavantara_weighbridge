# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_time, getdate, nowtime

RATE_BY_DELIVERY = {
	"Farmer Cane": "farmer_cane_rate",
	"Farm Delivery": "farm_delivery_rate",
	"Gate Cane": "gate_cane_rate",
	"Harvesting Machine": "harvesting_machine_rate",
}
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
		self.set_shift()
		if self.docstatus == 0:
			self.fetch_rates()
		self.validate_contractors()
		self.calculate_weights()
		if self.amended_from and not self.correction_reason:
			frappe.throw(_("Please enter the reason for the re-weighing / correction"))

	# --- defaults ---------------------------------------------------------------------
	def set_vehicle_defaults(self):
		if self.vehicle and not self.transport_contractor:
			self.transport_contractor = frappe.db.get_value("Weighbridge Vehicle", self.vehicle, "contractor")
		if self.farmer and not self.village:
			self.village = frappe.db.get_value("Cane Supplier", self.farmer, "village")
		if self.village and self.docstatus == 0:
			self.set_route_details()

	def set_route_details(self):
		"""Distance and transport rate come from the route (a row of the village's Routes table)."""
		routes = frappe.get_all(
			"Village Route", filters={"parent": self.village, "parenttype": "Village Master"},
			fields=["route", "distance_km", "transport_rate"], order_by="idx",
		)
		self.flags.route_rate = 0
		row = None
		if self.route:
			row = next((r for r in routes if r.route == self.route), None)
			if not row:
				frappe.throw(_("Route {0} does not belong to village {1}").format(self.route, self.village))
		elif len(routes) == 1:
			row = routes[0]
			self.route = row.route
		elif len(routes) > 1:
			frappe.throw(_("Village {0} has more than one route. Please select the route").format(self.village))
		if row:
			self.distance = flt(row.distance_km)
			self.flags.route_rate = flt(row.transport_rate)

	def set_shift(self):
		t = get_time(self.slip_time)
		self.shift = shift_for(t) or self.shift

	def fetch_rates(self):
		master = frappe.db.sql(
			"""select * from `tabCane Rate Master`
			where disabled = 0 and effective_from <= %(d)s and (effective_to is null or effective_to >= %(d)s)
			order by effective_from desc, creation desc limit 1""",
			{"d": getdate(self.slip_date)},
			as_dict=True,
		)
		if not master:
			frappe.throw(_("No active Cane Rate Master found for {0}").format(self.slip_date))
		m = master[0]
		village_rate = flt(self.flags.route_rate)
		self.cane_rate = flt(m.get(RATE_BY_DELIVERY.get(self.delivery_type, "farmer_cane_rate")))
		self.transport_rate = village_rate or flt(m.transport_rate)
		self.todani_rate = flt(m.todani_rate)
		self.farakt_rate = flt(m.farak_rate)
		self.harvesting_rate = flt(m.harvesting_machine_rate)

	def validate_contractors(self):
		for field, allowed in (("transport_contractor", ("Tractor", "Transport")),
							   ("cutting_contractor", ("Cutting Contractor", "Todani"))):
			c = self.get(field)
			if c:
				ctype = frappe.db.get_value("Contractor Master", c, "contractor_type")
				if ctype not in allowed:
					frappe.throw(
						_("{0} must be a {1} contractor").format(self.meta.get_label(field), _(" / ").join(allowed))
					)

	def calculate_weights(self):
		gross, tare = flt(self.gross_weight), flt(self.tare_weight)
		if gross < 0 or tare < 0 or flt(self.mat_weight) < 0 or flt(self.other_deduction) < 0:
			frappe.throw(_("Weights and deductions cannot be negative"))
		if gross and tare and gross <= tare:
			frappe.throw(_("Gross (loaded) weight must be greater than Tare (empty) weight"))
		self.cane_weight = flt(gross - tare, 2) if (gross and tare) else 0
		self.net_cane_weight = flt(self.cane_weight - flt(self.mat_weight) - flt(self.other_deduction), 2)
		if (flt(self.mat_weight) or flt(self.other_deduction)) and not self.deduction_reason:
			frappe.throw(_("Please enter the reason for the mat / other deduction"))

	# --- submit / cancel --------------------------------------------------------------
	def before_submit(self):
		if flt(self.net_cane_weight) <= 0:
			frappe.throw(_("Net Cane Weight must be greater than zero"))

	def on_cancel(self):
		billed = [self.get(f) for f in BILL_LINKS if self.get(f)]
		if billed:
			frappe.throw(_("Weighment Slip is already billed in {0}. Cancel the bill first.").format(", ".join(billed)))


def shift_for(t):
	for sh in frappe.get_all("Weighbridge Shift", filters={"disabled": 0}, fields=["name", "start_time", "end_time"]):
		start, end = get_time(sh.start_time), get_time(sh.end_time)
		if (start <= t < end) if start < end else (t >= start or t < end):
			return sh.name


@frappe.whitelist()
def get_shift(slip_time=None):
	"""Shift that covers the given time (default: now), used to fill the shift on the slip form."""
	return shift_for(get_time(slip_time or nowtime()))


@frappe.whitelist()
def get_indicator_weight():
	"""Read the current weight (Kg) from the weighbridge indicator configured in Weighbridge Settings."""
	frappe.has_permission("Weighment Slip", "create", throw=True)
	s = frappe.get_cached_doc("Weighbridge Settings")
	text = None
	if s.indicator_url:
		import requests

		try:
			text = requests.get(s.indicator_url, timeout=3).text
		except Exception as e:
			frappe.throw(_("Could not reach the weight indicator: {0}").format(e))
	elif s.indicator_serial_port:
		try:
			import serial
		except ImportError:
			frappe.throw(_("pyserial is not installed on the server. Use an indicator HTTP URL or install pyserial."))
		try:
			with serial.Serial(s.indicator_serial_port, cint(s.indicator_baud_rate) or 9600, timeout=2) as port:
				text = port.readline().decode(errors="ignore")
		except Exception as e:
			frappe.throw(_("Could not read the serial indicator: {0}").format(e))
	else:
		frappe.throw(_("Weight indicator is not configured. Enter the weight manually or set it up in Weighbridge Settings."))
	m = re.search(r"-?\d+(?:\.\d+)?", text or "")
	if not m:
		frappe.throw(_("No weight reading received from the indicator"))
	return flt(m.group())
