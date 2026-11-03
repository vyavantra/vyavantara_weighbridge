# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe

from vyavantra_weighbridge.vyavantra_weighbridge.report.weighment_register.weighment_register import (
	execute as register,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.status = "Cancelled"
	filters.group_by = "None"
	return register(filters)
