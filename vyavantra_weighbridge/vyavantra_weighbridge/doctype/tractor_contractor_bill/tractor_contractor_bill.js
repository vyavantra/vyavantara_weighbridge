// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

// 10% of the Total Amount is held back as deposit; same figure as DEPOSIT_PERCENT in tractor_contractor_bill.py
const TCB_DEPOSIT_PERCENT = 10;

frappe.ui.form.on("Tractor Contractor Bill", {
	setup(frm) {
		frm.set_query("contractor", () => ({ filters: { contractor_type: ["in", ["Tractor Contractor", "Tractor / Cutting Contractor"]], disabled: 0 } }));
		// rows come only from "Fetch Weighment Slips"; they can be removed but not added by hand
		frm.get_field("slips").grid.cannot_add_rows = true;
		vyavantra.weighbridge.bill_payment.setup(frm);
	},
	company(frm) {
		vyavantra.weighbridge.bill_payment.company(frm);
	},
	refresh(frm) {
		vyavantra.weighbridge.apply_card_theme(frm, {
			sb_payment: "💳",
			sb_weighment_slips: "🧾",
			sb_deductions: "➖",
			sb_payment_summary: "🧮",
		});
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Fetch Weighment Slips"), () => {
				frm.call("fetch_slips").then(() => frm.refresh_fields());
			}).addClass("btn-primary");
		}
		vyavantra.weighbridge.bill_payment.refresh(frm);
	},
	contractor(frm) {
		clear_slips(frm);
		frm.set_value("advance_deduction", 0);
		if (!frm.doc.contractor) return frm.set_value("outstanding_advance", 0);
		frappe.db.get_value("Contractor Master", frm.doc.contractor, "advance_balance").then((r) => {
			frm.set_value("outstanding_advance", flt((r.message || {}).advance_balance));
		});
	},
	commission_percent: calculate_totals,
	advance_deduction: calculate_totals,
	from_date: clear_slips,
	to_date: clear_slips,
});

frappe.ui.form.on("Tractor Bill Slip", {
	slips_remove: calculate_totals,
});

function clear_slips(frm) {
	if (frm.doc.docstatus === 0 && (frm.doc.slips || []).length) {
		frm.clear_table("slips");
		frm.refresh_field("slips");
		calculate_totals(frm);
	}
}

// Same sums as TractorContractorBill.calculate(); the server repeats them on save and is the authority.
function calculate_totals(frm) {
	if (frm.doc.docstatus !== 0) return;
	let quantity = 0, amount = 0, diesel_qty = 0, diesel = 0;
	(frm.doc.slips || []).forEach((row) => {
		quantity += flt(row.quantity);
		amount += flt(row.amount);
		diesel_qty += flt(row.diesel_qty);
		diesel += flt(row.diesel_amount);
	});
	const total = flt(amount, 2);
	const deposit = flt((total * TCB_DEPOSIT_PERCENT) / 100, 2);
	const commission = flt((total * flt(frm.doc.commission_percent)) / 100, 2);
	const recovery = flt(flt(frm.doc.advance_deduction) + deposit + flt(diesel, 2), 2);
	frm.set_value({
		total_quantity: flt(quantity, 3),
		total_amount: total,
		total_diesel_qty: flt(diesel_qty, 3),
		deposit_deduction: deposit,
		other_deduction: flt(diesel, 2),
		commission: commission,
		total_deductions: recovery,
		net_payable: flt(total + commission - recovery, 2),
	});
}
