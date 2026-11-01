// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tractor Contractor Bill", {
	setup(frm) {
		frm.set_query("contractor", () => ({ filters: { contractor_type: ["in", ["Tractor", "Transport"]], disabled: 0 } }));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Fetch Weighment Slips"), () => {
				frm.call("fetch_slips").then(() => frm.refresh_fields());
			}).addClass("btn-primary");
		}
		if (frm.doc.docstatus === 1 && flt(frm.doc.outstanding_amount) > 0) {
			frm.add_custom_button(__("Make Payment"), () => {
				frappe.new_doc("Weighbridge Payment", { bill_doctype: "Tractor Contractor Bill", bill: frm.doc.name });
			}).addClass("btn-primary");
		}
	},
	contractor(frm) {
		if (!frm.doc.contractor) return;
		frappe.db.get_value("Contractor Master", frm.doc.contractor, ["advance_balance", "deposit_balance"]).then((r) => {
			const b = r.message || {};
			frm.dashboard.set_headline(__("Advance balance: {0} | Deposit balance: {1}", [format_currency(b.advance_balance), format_currency(b.deposit_balance)]));
		});
	},
	from_date: clear_slips,
	to_date: clear_slips,
	contractor: clear_slips,
});

function clear_slips(frm) {
	if (frm.doc.docstatus === 0 && (frm.doc.slips || []).length) {
		frm.clear_table("slips");
		frm.refresh_field("slips");
	}
}
