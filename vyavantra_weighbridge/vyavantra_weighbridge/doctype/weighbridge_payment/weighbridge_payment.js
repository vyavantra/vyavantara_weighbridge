// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

const WP = "vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighbridge_payment.weighbridge_payment.";

frappe.ui.form.on("Weighbridge Payment", {
	refresh(frm) {
		frm.set_query("bill", () => ({ filters: { docstatus: 1, outstanding_amount: [">", 0] } }));
		if (frm.doc.docstatus === 1) {
			if (!frm.doc.journal_entry) {
				frm.add_custom_button(__("Create Journal Entry"), () => {
					frappe.call({ method: WP + "make_journal_entry", args: { name: frm.doc.name }, freeze: true })
						.then(() => frm.reload_doc());
				}, __("Accounting"));
			}
			if (frm.doc.mode !== "Cash" && !frm.doc.reconciled) {
				frm.add_custom_button(__("Mark Bank Reconciled"), () => {
					frappe.prompt({ fieldname: "clearance_date", fieldtype: "Date", label: __("Clearance Date"),
						default: frappe.datetime.get_today(), reqd: 1 }, (v) => {
						frappe.call({ method: WP + "mark_reconciled", args: { name: frm.doc.name, clearance_date: v.clearance_date } })
							.then(() => frm.reload_doc());
					}, __("Bank Reconciliation"));
				}, __("Accounting"));
			}
		}
	},
	bill(frm) {
		if (!frm.doc.bill || !frm.doc.bill_doctype) return;
		frappe.db.get_value(frm.doc.bill_doctype, frm.doc.bill,
			["outstanding_amount", "net_payable", "farmer_name", "contractor_name", "agent_name"]).then((r) => {
			const b = r.message || {};
			frm.set_value("outstanding_before", b.outstanding_amount);
			frm.set_value("bill_net_payable", b.net_payable);
			frm.set_value("party_name", b.farmer_name || b.contractor_name || b.agent_name);
			if (!frm.doc.amount) frm.set_value("amount", b.outstanding_amount);
		});
	},
});
