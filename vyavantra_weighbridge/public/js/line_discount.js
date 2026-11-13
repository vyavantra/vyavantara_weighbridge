// Row discount on Sales and Purchase Invoice: Qty and Rate stay as typed, the discount only lowers the
// line Amount. The server recalculates the same way on save (vyavantra_weighbridge/line_discount.py);
// this keeps the figures on screen in step while the operator types.
//
// calculate_item_values() is where ERPNext sets amount = rate * qty for every row, so the discount is
// taken off right after it, before anything is totalled.

frappe.provide("vyavantra.line_discount");

(function () {
	const CHILD_DOCTYPES = ["Sales Invoice Item", "Purchase Invoice Item"];
	const TRIGGERS = ["vw_discount_type", "vw_discount_value", "qty", "rate"];

	vyavantra.line_discount.of = function (row) {
		if (!row.vw_discount_type) return 0;

		const gross = flt(row.qty) * flt(row.rate);
		const value = flt(row.vw_discount_value);
		if (value <= 0) return 0;

		if (row.vw_discount_type === "Percentage") {
			return flt((gross * Math.min(value, 100)) / 100, precision("amount", row));
		}
		return flt(Math.min(value, Math.abs(gross)), precision("amount", row));
	};

	function patch_calculator() {
		const proto = erpnext.taxes_and_totals.prototype;
		if (proto.__vw_line_discount) return;
		proto.__vw_line_discount = true;

		const original = proto.calculate_item_values;
		proto.calculate_item_values = function () {
			original.call(this);

			// a document-level discount re-runs the whole calculation; the row discount is already in
			// the amounts by then and must not come off twice
			if (this.discount_amount_applied) return;
			if (!CHILD_DOCTYPES.includes((this.frm.doc.items || [])[0]?.doctype)) return;

			for (const item of this.frm.doc.items || []) {
				if (item.vw_discount_type === undefined) return; // custom fields not installed

				const discount = vyavantra.line_discount.of(item);
				item.vw_discount_amount = discount;
				if (!discount) continue;

				item.amount = flt(item.amount - discount, precision("amount", item));
				item.net_amount = item.amount;
				this.set_in_company_currency(item, ["amount", "net_amount"]);
			}
		};
	}

	// the controller classes load with the desk bundle, which may come after this file
	$(document).on("app_ready", patch_calculator);
	if (window.erpnext && erpnext.taxes_and_totals) patch_calculator();

	const handlers = {};
	TRIGGERS.forEach((field) => {
		handlers[field] = (frm) => frm.cscript.calculate_taxes_and_totals();
	});
	CHILD_DOCTYPES.forEach((child) => frappe.ui.form.on(child, handlers));
})();
