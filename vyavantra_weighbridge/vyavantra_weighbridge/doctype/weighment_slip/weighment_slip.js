// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

const WS_PATH = "vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip.";

// the Field Slip details that identify the vehicle; without them a captured weight cannot be placed
const REQUIRED_BEFORE_WEIGHT = ["farmer", "delivery_type", "vehicle"];
// the slip is saved right after each weighing, so a reading is never lost
const AUTO_SAVE_AFTER_FETCH = true;

frappe.ui.form.on("Weighment Slip", {
	setup(frm) {
		// each contractor field lists only the contractors of its own type
		frm.set_query("transport_contractor", () => ({ filters: { contractor_type: ["in", ["Tractor", "Both"]], disabled: 0 } }));
		frm.set_query("cutting_contractor", () => ({ filters: { contractor_type: ["in", ["Cutting Contractor", "Both"]], disabled: 0 } }));
		frm.set_query("farmer", () => ({ filters: { disabled: 0 } }));
		frm.set_query("agent", () => ({ filters: { disabled: 0 } }));
		frm.set_query("delivery_type", () => ({ filters: { disabled: 0 } }));
		// only the routes that are defined in the member's village
		frm.set_query("route", () => ({
			query: "vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip.route_query",
			filters: { village: frm.doc.village || "" },
		}));
	},
	refresh(frm) {
		frm.page.wrapper.addClass("wbs-slip"); // scopes weighment_slip.css to this form only
		format_computed_weights(frm);
		show_time_in_12_hour(frm);
		if (frm.doc.docstatus === 0) {
			set_fetch_label(frm);
			if (!frm.is_new()) load_binding_percent(frm);
			// Fetch Weight takes the next missing weighing; these two take a named one, so an operator
			// can re-read just the loaded or just the empty vehicle
			frm.add_custom_button(__("Loaded Vehicle Weight"), () => capture(frm, "gross_weight"), __("Capture"));
			frm.add_custom_button(__("Empty Vehicle Weight"), () => capture(frm, "tare_weight"), __("Capture"));
			if (frm.is_new()) {
				show_cane_rates(frm);
				set_shift(frm);
			}
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Print Slip"), () => frm.print_doc());
		}
	},
	vehicle(frm) {
		if (!frm.doc.vehicle) return;
		// the Tractor contractor that owns this tractor number, if it has exactly one
		frappe.call({ method: WS_PATH + "get_tractor_contractor", args: { tractor: frm.doc.vehicle } }).then((r) => {
			if (r.message) frm.set_value("transport_contractor", r.message);
		});
	},
	farmer(frm) {
		// the village comes from the member; the old route/distance/rate belong to the previous village
		clear_route(frm);
		if (!frm.doc.farmer) {
			frm.set_value("village", "");
			return;
		}
		frappe.db.get_value("Cane Supplier", frm.doc.farmer, "village").then((r) => {
			const village = (r.message && r.message.village) || "";
			frm.set_value("village", village);
			pick_single_route(frm, village);
		});
	},
	route(frm) {
		if (!frm.doc.route) return clear_route(frm);
		frappe.call({
			method: WS_PATH + "get_village_routes",
			args: { village: frm.doc.village },
			callback: (r) => {
				const row = (r.message || []).find((x) => x.route === frm.doc.route);
				if (!row) {
					frappe.msgprint(__("Route {0} is not defined for village {1}", [frm.doc.route, frm.doc.village]));
					return clear_route(frm);
				}
				frm.set_value("distance", row.distance_km);
				frm.set_value("transport_rate", row.transport_rate);
			},
		});
	},
	delivery_type: show_cane_rates,
	slip_date: show_cane_rates,
	slip_time(frm) {
		set_shift(frm);
		show_time_in_12_hour(frm);
	},
	after_save(frm) {
		format_computed_weights(frm);
		set_fetch_label(frm);
	},
	on_hide(frm) {
		frm.page.wrapper.removeClass("wbs-slip");
	},
	fetch_weight(frm) {
		fetch_next_weight(frm);
	},
	gross_weight(frm) {
		calc(frm);
		set_fetch_label(frm);
	},
	tare_weight(frm) {
		calc(frm);
		set_fetch_label(frm);
	},
	other_deduction_percent: calc,
});

// the shift is decided by the slip time, never typed by hand
function set_shift(frm) {
	if (frm.doc.docstatus !== 0) return;
	if (!frm.doc.slip_time) return frm.set_value("shift", "");
	frappe.call({
		method: WS_PATH + "get_shift",
		args: { slip_time: frm.doc.slip_time },
		callback: (r) => frm.set_value("shift", r.message || ""),
	});
}

// The time is typed and stored on the 24 hour clock, which is what the shifts are set in. The same
// time is spelled out underneath, so an operator reading 20:30 off the slip sees 8:30 PM as well.
function show_time_in_12_hour(frm) {
	const time = frm.doc.slip_time;
	if (!time) return frm.set_df_property("slip_time", "description", "");

	const spoken = moment(time, "HH:mm:ss").format("h:mm A");
	frm.set_df_property("slip_time", "description", __("24 hour clock. {0} is {1}", [time.slice(0, 5), spoken]));
}

function clear_route(frm) {
	if (frm.doc.route) frm.set_value("route", "");
	frm.set_value("distance", 0);
	frm.set_value("transport_rate", 0);
}

// a village with exactly one route needs no choice
function pick_single_route(frm, village) {
	if (!village) return;
	frappe.call({
		method: WS_PATH + "get_village_routes",
		args: { village },
		callback: (r) => {
			const routes = r.message || [];
			if (routes.length === 1) frm.set_value("route", routes[0].route);
		},
	});
}

// Cane Rate Master rates of the chosen delivery type, for the slip date; shown before the slip is saved
function show_cane_rates(frm) {
	if (frm.doc.docstatus !== 0) return;
	if (!frm.doc.delivery_type) {
		["cane_rate", "todani_rate", "farakt_rate"].forEach((field) => frm.set_value(field, 0));
		frm.binding_percent = 0;
		calc(frm);
		return;
	}
	frappe.call({
		method: WS_PATH + "get_cane_rates",
		args: { slip_date: frm.doc.slip_date, delivery_type: frm.doc.delivery_type },
		callback: (r) => {
			const rates = r.message || {};
			const found = rates.cane_rate !== undefined;
			frm.set_value("cane_rate", found ? rates.cane_rate : 0);
			frm.set_value("todani_rate", found ? rates.todani_rate : 0);
			frm.set_value("farakt_rate", found ? rates.farakt_rate : 0);
			frm.binding_percent = found ? flt(rates.binding_deduction_percent) : 0;
			calc(frm);
			if (!found) {
				frappe.show_alert({
					message: __("No Cane Rate Master has a rate for {0} on {1}", [
						frm.doc.delivery_type,
						frappe.datetime.str_to_user(frm.doc.slip_date) || __("today"),
					]),
					indicator: "orange",
				});
			}
		},
	});
}

// The Binding Deduction % belongs to the Cane Rate Master of the slip's date and delivery type. A saved draft
// reads it again when it is opened, so editing its weights recalculates the binding the same way the server will.
function load_binding_percent(frm) {
	if (!frm.doc.delivery_type) return;
	frappe.call({
		method: WS_PATH + "get_cane_rates",
		args: { slip_date: frm.doc.slip_date, delivery_type: frm.doc.delivery_type },
		callback: (r) => (frm.binding_percent = flt((r.message || {}).binding_deduction_percent)),
	});
}

// Whole kilograms, half rounded up (2.5 -> 3), exactly as round_kg() / percent_of_kg() in weighment_slip.py.
// The value is cut to 12 significant digits first so binary float noise (2.4999999999999996) cannot flip a half.
function kg(value) {
	return Math.round(Number(flt(value).toPrecision(12)));
}

// Same chain as WeighmentSlip.calculate_weights(); the server repeats it on save and is the authority.
// It runs whenever any input changes, so typing only the Loaded Vehicle Weight already fills everything below it.
function calc(frm) {
	if (frm.doc.docstatus !== 0) return;
	const loaded = kg(frm.doc.gross_weight), empty = kg(frm.doc.tare_weight);
	const percent = Math.min(Math.max(flt(frm.doc.other_deduction_percent), 0), 100);
	const cane = loaded ? loaded - empty : 0;
	const binding = kg((cane * flt(frm.binding_percent)) / 100);
	const net_after_binding = cane - binding;
	const deduction = kg((net_after_binding * percent) / 100);
	frm.set_value("cane_weight", cane);
	frm.set_value("mat_weight", binding);
	frm.set_value("net_after_binding", net_after_binding);
	frm.set_value("other_deduction", deduction);
	frm.set_value("net_cane_weight", net_after_binding - deduction);
	setTimeout(() => format_computed_weights(frm), 50);
}

// weight and capture time of each weighing; the scale must also agree with the weighing already taken
const WEIGHT_TIME_FIELD = { gross_weight: "gross_weight_time", tare_weight: "tare_weight_time" };

// Fetch Weight takes the weighing that is still missing: loaded first, empty after unloading.
// With both already taken the operator picks the one to read again.
async function fetch_next_weight(frm) {
	if (frm.doc.docstatus !== 0) return;

	const missing = REQUIRED_BEFORE_WEIGHT.filter((f) => frm.fields_dict[f] && !frm.doc[f]).map((f) =>
		__(frm.fields_dict[f].df.label)
	);
	if (missing.length) {
		return frappe.msgprint({
			title: __("Fill Field Slip details first"),
			indicator: "orange",
			message: __("Please fill: {0}", [missing.join(", ")]),
		});
	}

	let field;
	if (!flt(frm.doc.gross_weight)) field = "gross_weight";
	else if (!flt(frm.doc.tare_weight)) field = "tare_weight";
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
				resolve(values.which === __("Loaded Vehicle Weight") ? "gross_weight" : "tare_weight");
			},
		});
		d.onhide = () => resolve(null); // closed without choosing
		d.show();
	});
}

// "Fetch Loaded Weight" -> "Fetch Empty Weight" -> "Fetch Weight", so the button says what it will do next
function set_fetch_label(frm) {
	if (!frm.fields_dict.fetch_weight) return;
	let label = __("Fetch Weight");
	if (!flt(frm.doc.gross_weight)) label = __("Fetch Loaded Weight");
	else if (!flt(frm.doc.tare_weight)) label = __("Fetch Empty Weight");
	frm.set_df_property("fetch_weight", "label", label);
}

function capture(frm, field) {
	return vyavantra.weighbridge.capture(frm, field, {
		time_field: WEIGHT_TIME_FIELD[field],
		transform: kg, // weights are whole kilograms
		check: (weight) => {
			const loaded = flt(frm.doc.gross_weight), empty = flt(frm.doc.tare_weight);
			if (field === "tare_weight" && loaded && weight >= loaded) {
				return __("Scale shows {0} kg, but Loaded Vehicle Weight is {1} kg. Is the vehicle unloaded?", [weight, loaded]);
			}
			if (field === "gross_weight" && empty && weight <= empty) {
				return __("Scale shows {0} kg, but Empty Vehicle Weight is {1} kg. Is the vehicle loaded?", [weight, empty]);
			}
		},
		after: async () => {
			if (!AUTO_SAVE_AFTER_FETCH || !frm.is_dirty()) return;
			try {
				await frm.save();
			} catch (e) {
				// Frappe already shows why the save failed, e.g. a missing mandatory field
			}
		},
	});
}

// weights tab layout: public/css/weighment_slip.css
const COMPUTED_WEIGHTS = ["cane_weight", "mat_weight", "net_after_binding", "other_deduction", "net_cane_weight"];

// computed weights are read-only, which Frappe prints as a bare "0"; show them as whole kilograms with digit grouping
function format_computed_weights(frm) {
	COMPUTED_WEIGHTS.forEach((name) => {
		const field = frm.fields_dict[name];
		if (field) field.$wrapper.find(".control-value").text(format_number(kg(frm.doc[name]), null, 0));
	});
}
