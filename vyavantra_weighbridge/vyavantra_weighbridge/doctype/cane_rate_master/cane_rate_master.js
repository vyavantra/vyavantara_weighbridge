// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cane Rate Master", {
	setup(frm) {
		frm.set_query("delivery_type", "rates", () => ({ filters: { disabled: 0 } }));
	},
	refresh(frm) {
		// a new master starts with one row per enabled Delivery Type, only the rates are left to fill
		// (Frappe already adds one empty row to a required table, so "empty" means no rate entered yet)
		const untouched = (frm.doc.rates || []).every((row) => !row.cane_rate);
		if (!frm.is_new() || !untouched) return;
		frappe.db.get_list("Delivery Type", { filters: { disabled: 0 }, pluck: "name", order_by: "creation", limit: 50 }).then((types) => {
			if (!frm.is_new() || !(frm.doc.rates || []).every((row) => !row.cane_rate)) return;
			frm.clear_table("rates");
			types.forEach((delivery_type) => frm.add_child("rates", { delivery_type }));
			frm.refresh_field("rates");
		});
	},
});
