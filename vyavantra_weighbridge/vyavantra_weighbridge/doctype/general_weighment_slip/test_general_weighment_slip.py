# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


def make_slip(**kw):
	values = {
		"doctype": "General Weighment Slip",
		"product_name": frappe.db.get_value("Item", {}, "name"),
		"vehicle_type": "Tanker",
		"vehicle_no": frappe.db.get_value("Tractor Number", {}, "name"),
		"party_name": frappe.db.get_value("Supplier", {}, "name"),
		"loaded_weight": 30000,
		"empty_weight": 12000,
	}
	values.update(kw)
	return frappe.get_doc(values)


class TestGeneralWeighmentSlip(FrappeTestCase):
	def test_net_weight_is_loaded_minus_empty_whatever_the_client_sent(self):
		slip = make_slip(net_weight=1)
		slip.insert()
		self.assertEqual(slip.net_weight, 18000)

	def test_loaded_must_be_heavier_than_empty(self):
		with self.assertRaises(frappe.ValidationError):
			make_slip(loaded_weight=1000, empty_weight=2000).insert()

	def test_net_follows_loaded_weight_until_empty_weight_is_taken_and_blocks_submit(self):
		slip = make_slip(empty_weight=0).insert()
		self.assertEqual(slip.net_weight, 30000)
		with self.assertRaises(frappe.ValidationError):
			slip.submit()

	def test_serial_restarts_each_day(self):
		a = make_slip(slip_date="2026-11-04").insert()
		b = make_slip(slip_date="2026-11-04").insert()
		c = make_slip(slip_date="2026-11-05").insert()
		self.assertEqual((a.serial_no, b.serial_no, c.serial_no), (a.serial_no, a.serial_no + 1, 1))
