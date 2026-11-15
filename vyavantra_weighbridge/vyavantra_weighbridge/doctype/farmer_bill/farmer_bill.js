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
		// the workflow carries the bill from here: Actions > Pay books the Payment Entry
		if (frm.doc.workflow_status === "Unpaid" && !(frm.doc.reference_no && frm.doc.reference_date)) {
			frm.set_intro(
				__("After the bank confirms the payment, enter the Reference No and Reference Date, save, and choose Actions > Pay."),
				"blue"
			);
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
