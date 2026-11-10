# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.utils import cint, flt


def read_indicator_weight():
	"""Current weight (Kg) from the weighbridge indicator configured in Weighbridge Settings."""
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


@frappe.whitelist()
def get_indicator_config():
	"""How the browser should read the weight. Weighbridge Settings is readable by managers only, but every
	user who can create a slip has to be able to press Fetch Weight."""
	if not any(frappe.has_permission(dt, "create") for dt in ("Weighment Slip", "General Weighment Slip")):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	s = frappe.get_cached_doc("Weighbridge Settings")
	return {
		"source": s.indicator_source or "Server",
		"baud_rate": cint(s.indicator_baud_rate) or 9600,
		"parity": s.indicator_parity or "none",
		"data_bits": cint(s.indicator_data_bits) or 8,
		"stop_bits": cint(s.indicator_stop_bits) or 1,
		"stable_readings": cint(s.indicator_stable_readings) or 3,
		"service_url": (s.indicator_service_url or "").strip(),
		"service_timeout_ms": cint(s.indicator_service_timeout) or 15000,
	}
