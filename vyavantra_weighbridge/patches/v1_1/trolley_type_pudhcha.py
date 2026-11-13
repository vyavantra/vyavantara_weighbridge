"""Weighment Slip: the Trolley Type option word पक्का is now पुढचा (e.g. "पक्का ट्रेलर वरची वायर" ->
"पुढचा ट्रेलर वरची वायर"). The rest of each option is kept. Idempotent."""

import frappe


def execute():
	frappe.db.sql(
		"""update `tabWeighment Slip` set trolley_type = replace(trolley_type, 'पक्का', 'पुढचा')
		where trolley_type like %s""",
		"%पक्का%",
	)
