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
