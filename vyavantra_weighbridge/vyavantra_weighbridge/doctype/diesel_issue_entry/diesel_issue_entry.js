// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

const DIESEL_PAVTI_FORMAT = "Diesel Issue Slip";

frappe.ui.form.on("Diesel Issue Entry", {
	setup(frm) {
		frm.set_query("disel_receiver_name", () => ({ filters: { contractor_type: ["in", ["Tractor Contractor", "Tractor / Cutting Contractor"]], disabled: 0 } }));
	},
	refresh(frm) {
		vyavantra.weighbridge.apply_card_theme(frm);
		if (!frm.is_new() && frm.doc.docstatus < 2) {
			frm.add_custom_button(__("Print Diesel Pavti"), () => {
				frm.meta.default_print_format = DIESEL_PAVTI_FORMAT;
				frm.print_doc();
			}).addClass("btn-primary");
		}
	},
	tractor_number(frm) {
		// diesel issued on its own is recovered from the contractor who owns the tractor
		if (frm.doc.weighment_slip || !frm.doc.tractor_number) return;
		frappe.call({
			method: "vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip.get_tractor_contractor",
			args: { tractor: frm.doc.tractor_number },
		}).then((r) => {
			if (r.message) frm.set_value("disel_receiver_name", r.message);
		});
	},
});
