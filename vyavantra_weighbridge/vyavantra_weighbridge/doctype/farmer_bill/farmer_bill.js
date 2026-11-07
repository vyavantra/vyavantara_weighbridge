// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Farmer Bill", {
	setup(frm) {
		// the slips come only from "Fetch Weighment Slips" (by farmer and dates); rows can be removed but not added by hand
		frm.get_field("slips").grid.cannot_add_rows = true;
	},
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Fetch Weighment Slips"), () => {
				frm.call("fetch_slips").then(() => frm.refresh_fields());
			}).addClass("btn-primary");
		}
		if (frm.doc.docstatus === 1 && flt(frm.doc.outstanding_amount) > 0) {
			frm.add_custom_button(__("Make Payment"), () => {
				frappe.new_doc("Weighbridge Payment", { bill_doctype: "Farmer Bill", bill: frm.doc.name });
			}).addClass("btn-primary");
		}
	},
	from_date: clear_slips,
	to_date: clear_slips,
	farmer: clear_slips,
});

function clear_slips(frm) {
	if (frm.doc.docstatus === 0 && (frm.doc.slips || []).length) {
		frm.clear_table("slips");
		frm.refresh_field("slips");
	}
}
