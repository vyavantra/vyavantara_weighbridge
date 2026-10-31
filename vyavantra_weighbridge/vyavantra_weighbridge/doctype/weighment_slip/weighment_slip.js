// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

const WS_METHOD = "vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip.get_indicator_weight";

frappe.ui.form.on("Weighment Slip", {
	setup(frm) {
		frm.set_query("transport_contractor", () => ({
			filters: { contractor_type: ["in", ["Tractor", "Transport"]], disabled: 0 },
		}));
		frm.set_query("cutting_contractor", () => ({
			filters: { contractor_type: ["in", ["Cutting", "Todani"]], disabled: 0 },
		}));
		frm.set_query("vehicle", () => ({ filters: { disabled: 0 } }));
		frm.set_query("farmer", () => ({ filters: { disabled: 0 } }));
		frm.set_query("agent", () => ({ filters: { disabled: 0 } }));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Capture Gross Weight"), () => capture(frm, "gross_weight"), __("Indicator"));
			frm.add_custom_button(__("Capture Tare Weight"), () => capture(frm, "tare_weight"), __("Indicator"));
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Print Slip"), () => frm.print_doc());
		}
	},
	vehicle(frm) {
		if (!frm.doc.vehicle) return;
		frappe.db.get_value("Weighbridge Vehicle", frm.doc.vehicle, "contractor").then((r) => {
			if (r.message && r.message.contractor) frm.set_value("transport_contractor", r.message.contractor);
		});
	},
	gross_weight: calc,
	tare_weight: calc,
	mat_weight: calc,
	other_deduction: calc,
});

function calc(frm) {
	const gross = flt(frm.doc.gross_weight), tare = flt(frm.doc.tare_weight);
	const cane = gross && tare ? gross - tare : 0;
	frm.set_value("cane_weight", cane);
	frm.set_value("net_cane_weight", cane - flt(frm.doc.mat_weight) - flt(frm.doc.other_deduction));
}

function capture(frm, field) {
	frappe.call({
		method: WS_METHOD,
		freeze: true,
		freeze_message: __("Reading weight indicator..."),
		callback: (r) => {
			if (r.message !== undefined) frm.set_value(field, r.message);
		},
	});
}
