// Payment part of the bills that are paid through the workflow (Farmer Bill, Tractor Contractor Bill):
// the bill is saved as Unpaid, the accounts and the bank reference are chosen on it, and Actions > Pay books it.

frappe.provide("vyavantra.weighbridge");

vyavantra.weighbridge.bill_payment = {
	setup(frm) {
		frm.set_query("paid_from", () => ({
			filters: { company: frm.doc.company, is_group: 0, account_type: ["in", ["Bank", "Cash"]] },
		}));
		// the party itself is added by the payment; here goes the account the bill is booked to
		frm.set_query("paid_to", () => ({
			filters: { company: frm.doc.company, is_group: 0, account_type: ["not in", ["Receivable", "Payable"]] },
		}));
	},

	refresh(frm) {
		if (frm.is_new()) {
			frappe
				.call({ method: "vyavantra_weighbridge.billing.get_payment_defaults", args: { doctype: frm.doctype } })
				.then((r) => {
					Object.entries(r.message || {}).forEach(([field, value]) => {
						if (value && !frm.doc[field]) frm.set_value(field, value);
					});
				});
			return;
		}
		// if (frm.doc.docstatus === 0) {
		// 	frm.set_intro(
		// 		__("After the bank confirms the payment, choose Paid From and Paid To, enter the Reference No and Reference Date, save, and choose Actions > Pay."),
		// 		"blue"
		// 	);
		// }
	},

	// accounts belong to a company: changing it empties the ones chosen for the old company
	company(frm) {
		["paid_from", "paid_to"].forEach((field) => {
			if (!frm.doc[field]) return;
			frappe.db.get_value("Account", frm.doc[field], "company").then((r) => {
				if (r.message && r.message.company !== frm.doc.company) frm.set_value(field, null);
			});
		});
	},
};
