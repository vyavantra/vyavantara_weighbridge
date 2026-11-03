// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Agent Bill", {
	setup(frm) {
	},
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Fetch Weighment Slips"), () => {
				frm.call("fetch_slips").then(() => frm.refresh_fields());
			}).addClass("btn-primary");
		}
		if (frm.doc.docstatus === 1 && flt(frm.doc.outstanding_amount) > 0) {
			frm.add_custom_button(__("Make Payment"), () => {
				frappe.new_doc("Weighbridge Payment", { bill_doctype: "Agent Bill", bill: frm.doc.name });
			}).addClass("btn-primary");
		}
	},
	agent(frm) {
		if (!frm.doc.agent) return;
		frappe.db.get_value("Cane Agent", frm.doc.agent, ["commission_rate", "advance_balance"]).then((r) => {
			const b = r.message || {};
			frm.set_value("commission_rate", b.commission_rate);
			frm.dashboard.set_headline(__("Advance balance: {0}", [format_currency(b.advance_balance)]));
		});
	},
	from_date: clear_slips,
	to_date: clear_slips,
	agent: clear_slips,
});

function clear_slips(frm) {
	if (frm.doc.docstatus === 0 && (frm.doc.slips || []).length) {
		frm.clear_table("slips");
		frm.refresh_field("slips");
	}
}
