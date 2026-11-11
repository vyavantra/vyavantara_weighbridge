// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

// the details that identify the load; without them a captured weight cannot be placed
const GWS_REQUIRED_BEFORE_WEIGHT = ["product_name", "vehicle_no", "party_name"];
const GWS_AUTO_SAVE_AFTER_FETCH = true;

frappe.ui.form.on("General Weighment Slip", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			set_fetch_label(frm);
			// Fetch Weight takes the next missing weighing; these two take a named one
			frm.add_custom_button(__("Loaded Vehicle Weight"), () => capture(frm, "loaded_weight"), __("Capture"));
			frm.add_custom_button(__("Empty Vehicle Weight"), () => capture(frm, "empty_weight"), __("Capture"));
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Print Slip"), () => frm.print_doc());
		}
	},
	after_save: set_fetch_label,
	fetch_weight(frm) {
		fetch_next_weight(frm);
	},
	loaded_weight(frm) {
		calc(frm);
		set_fetch_label(frm);
	},
	empty_weight(frm) {
		calc(frm);
		set_fetch_label(frm);
	},
});

// Same as GeneralWeighmentSlip.calculate_weights(); the server repeats it on save.
function calc(frm) {
	if (frm.doc.docstatus !== 0) return;
	const loaded = flt(frm.doc.loaded_weight), empty = flt(frm.doc.empty_weight);
	frm.set_value("net_weight", loaded ? flt(loaded - empty, 2) : 0);
}

// Fetch Weight takes the weighing that is still missing; with both taken the operator picks one to redo
async function fetch_next_weight(frm) {
	if (frm.doc.docstatus !== 0) return;

	const missing = GWS_REQUIRED_BEFORE_WEIGHT.filter((f) => frm.fields_dict[f] && !frm.doc[f]).map((f) =>
		__(frm.fields_dict[f].df.label)
	);
	if (missing.length) {
		return frappe.msgprint({
			title: __("Fill the slip details first"),
			indicator: "orange",
			message: __("Please fill: {0}", [missing.join(", ")]),
		});
	}

	let field;
	if (!flt(frm.doc.loaded_weight)) field = "loaded_weight";
	else if (!flt(frm.doc.empty_weight)) field = "empty_weight";
	else field = await ask_which_weight();
	if (field) await capture(frm, field);
}

function ask_which_weight() {
	return new Promise((resolve) => {
		const d = new frappe.ui.Dialog({
			title: __("Both weights are already taken"),
			fields: [
				{
					fieldname: "which",
					fieldtype: "Select",
					label: __("Take again"),
					options: [__("Loaded Vehicle Weight"), __("Empty Vehicle Weight")].join("\n"),
					default: __("Empty Vehicle Weight"),
					reqd: 1,
				},
			],
			primary_action_label: __("Fetch"),
			primary_action(values) {
				d.hide();
				resolve(values.which === __("Loaded Vehicle Weight") ? "loaded_weight" : "empty_weight");
			},
		});
		d.onhide = () => resolve(null);
		d.show();
	});
}

// "Fetch Loaded Weight" -> "Fetch Empty Weight" -> "Fetch Weight"
function set_fetch_label(frm) {
	if (frm.doc.docstatus !== 0 || !frm.fields_dict.fetch_weight) return;
	let label = __("Fetch Weight");
	if (!flt(frm.doc.loaded_weight)) label = __("Fetch Loaded Weight");
	else if (!flt(frm.doc.empty_weight)) label = __("Fetch Empty Weight");
	frm.set_df_property("fetch_weight", "label", label);
}

function capture(frm, field) {
	return vyavantra.weighbridge.capture(frm, field, {
		check: (weight) => {
			const loaded = flt(frm.doc.loaded_weight), empty = flt(frm.doc.empty_weight);
			if (field === "empty_weight" && loaded && weight >= loaded) {
				return __("Scale shows {0} kg, but Loaded Vehicle Weight is {1} kg. Is the vehicle unloaded?", [weight, loaded]);
			}
			if (field === "loaded_weight" && empty && weight <= empty) {
				return __("Scale shows {0} kg, but Empty Vehicle Weight is {1} kg. Is the vehicle loaded?", [weight, empty]);
			}
		},
		after: async () => {
			if (!GWS_AUTO_SAVE_AFTER_FETCH || !frm.is_dirty()) return;
			try {
				await frm.save();
			} catch (e) {
				// Frappe already shows why the save failed
			}
		},
	});
}
