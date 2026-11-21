// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Village Master", {
	refresh(frm) {
		vyavantra.weighbridge.apply_card_theme(frm, {
			sb_routes: "🛣️",
		});
	},
});
