"""Line discount that leaves Qty and Rate alone.

A factory bill is read as "3 nos at 9, less 2%". The rate is what was agreed with the supplier, so it
must still read 9 on the invoice; only the line total drops. ERPNext's own Discount (%) / Discount
Amount do the opposite: they divide the discount into the rate (9 becomes 8.82) and only appear once a
Price List Rate is filled in.

Only `amount` is changed. Everything downstream is derived from it, so the net total, GST, the GL
entries, the outstanding, Payment Entry and the registers follow by themselves.
"""

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals

PERCENTAGE = "Percentage"
AMOUNT = "Amount"


def line_discount(item):
	"""Discount of one row in document currency, after validating what the operator typed."""
	discount_type = item.get("vw_discount_type")
	if not discount_type:
		return 0.0

	value = flt(item.get("vw_discount_value"))
	gross = flt(flt(item.qty) * flt(item.rate), item.precision("amount"))

	if value < 0:
		frappe.throw(_("Row {0}: Discount cannot be negative").format(item.idx))

	if discount_type == PERCENTAGE:
		if value > 100:
			frappe.throw(_("Row {0}: Discount cannot be more than 100%").format(item.idx))
		return flt(gross * value / 100, item.precision("amount"))

	if value > abs(gross):
		frappe.throw(
			_("Row {0}: Discount of {1} is more than the amount of the row, {2}").format(
				item.idx,
				frappe.format(value, {"fieldtype": "Currency"}),
				frappe.format(gross, {"fieldtype": "Currency"}),
			)
		)
	return flt(value, item.precision("amount"))


class LineDiscountTaxesAndTotals(calculate_taxes_and_totals):
	"""ERPNext's calculator, with the row discount taken off each line amount.

	calculate_item_values() is where ERPNext sets `amount = rate * qty`; the discount is applied right
	after, before anything is totalled, so every later step already sees the discounted amount.
	"""

	def calculate_item_values(self):
		super().calculate_item_values()

		# a document-level discount re-runs the whole calculation; the row discount is already in the
		# amounts at that point and must not be taken off a second time
		if self.discount_amount_applied:
			return

		for item in self._items:
			if not item.meta.has_field("vw_discount_type"):
				return  # custom fields not installed yet (first migrate)

			discount = line_discount(item)
			item.vw_discount_amount = discount
			if not discount:
				continue

			item.amount = flt(item.amount - discount, item.precision("amount"))
			item.net_amount = item.amount
			self._set_in_company_currency(item, ["amount", "net_amount"])


class LineDiscountInvoice:
	"""Mixin for the two invoice classes: the stock calculation with the row discount in it."""

	def calculate_taxes_and_totals(self):
		LineDiscountTaxesAndTotals(self)

		if self.doctype == "Sales Invoice":
			self.calculate_commission()
			self.calculate_contribution()


class LineDiscountPurchaseInvoice(LineDiscountInvoice, PurchaseInvoice):
	pass


class LineDiscountSalesInvoice(LineDiscountInvoice, SalesInvoice):
	pass
