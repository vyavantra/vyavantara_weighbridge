# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate

GROUPS = ("Farm", "GateCane", "Harvesting Machine")
# delivery type on the slip -> vehicle group printed on the reports
GROUP_OF = {"Farmer Cane": "Farm", "Farm Delivery": "Farm", "Gate Cane": "GateCane", "Harvesting Machine": "Harvesting Machine"}


def group_of(delivery_type):
	return GROUP_OF.get(delivery_type or "", "Farm")


def tons(kg):
	return round(flt(kg) / 1000.0, 3)


def check_access():
	frappe.has_permission("Weighment Slip", "report", throw=True)


def fmt_date(d):
	return getdate(d).strftime("%d/%m/%Y")


@frappe.whitelist()
def get_report_heading():
	s = frappe.get_cached_doc("Weighbridge Settings")
	company = s.report_company_name or s.company or frappe.defaults.get_global_default("company") or ""
	return {"company": company, "address": s.report_address or "", "phone": s.report_phone or ""}
