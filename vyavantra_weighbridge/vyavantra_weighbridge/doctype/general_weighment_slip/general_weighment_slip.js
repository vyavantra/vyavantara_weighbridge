// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

const GWS_METHOD = "vyavantra_weighbridge.vyavantra_weighbridge.doctype.general_weighment_slip.general_weighment_slip.get_indicator_weight";

frappe.ui.form.on("General Weighment Slip", {
	refresh(frm) {
		frm.page.add_menu_item(__("Select Weighbridge COM Port"), () => vyavantra.weighbridge.select_port());
		if (frm.doc.docstatus === 0) {
			// Fetch Weight takes the next missing weighing; these two take a named one
			frm.add_custom_button(__("Loaded Vehicle Weight"), () => capture(frm, "loaded_weight"), __("Capture"));
			frm.add_custom_button(__("Empty Vehicle Weight"), () => capture(frm, "empty_weight"), __("Capture"));
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Print Slip"), () => frm.print_doc());
		}
	},
	fetch_weight(frm) {
		// the first reading is the loaded vehicle, the next one the empty vehicle
		if (!flt(frm.doc.loaded_weight)) return capture(frm, "loaded_weight");
		if (!flt(frm.doc.empty_weight)) return capture(frm, "empty_weight");
		frappe.show_alert({ message: __("Loaded and Empty Vehicle Weights are already taken. Edit a weight to read it again."), indicator: "orange" });
	},
	loaded_weight: calc,
	empty_weight: calc,
});

// Same as GeneralWeighmentSlip.calculate_weights(); the server repeats it on save.
function calc(frm) {
	if (frm.doc.docstatus !== 0) return;
	const loaded = flt(frm.doc.loaded_weight), empty = flt(frm.doc.empty_weight);
	frm.set_value("net_weight", loaded ? flt(loaded - empty, 2) : 0);
}

function capture(frm, field) {
	return vyavantra.weighbridge.capture(frm, field, GWS_METHOD, {
		check: (weight) => {
			const loaded = flt(frm.doc.loaded_weight), empty = flt(frm.doc.empty_weight);
			if (field === "empty_weight" && loaded && weight >= loaded) {
				return __("Scale shows {0} kg, but Loaded Vehicle Weight is {1} kg. Is the vehicle unloaded?", [weight, loaded]);
			}
			if (field === "loaded_weight" && empty && weight <= empty) {
				return __("Scale shows {0} kg, but Empty Vehicle Weight is {1} kg. Is the vehicle loaded?", [weight, empty]);
			}
		},
	});
}
