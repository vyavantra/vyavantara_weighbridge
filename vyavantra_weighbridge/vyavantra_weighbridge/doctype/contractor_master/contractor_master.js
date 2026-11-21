// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Contractor Master", {
	refresh(frm) {
		vyavantra.weighbridge.apply_card_theme(frm, {
			sb_contractor_info: "📋",
			sb_tractors: "🚜",
			sb_advance_deposit: "💰",
			sb_bank: "🏦",
		});
	},
});
