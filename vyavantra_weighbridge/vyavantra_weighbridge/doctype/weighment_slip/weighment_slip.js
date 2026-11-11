// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

const WS_PATH = "vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip.";
const WS_METHOD = WS_PATH + "get_indicator_weight";

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
		frm.page.add_menu_item(__("Select Weighbridge COM Port"), () => vyavantra.weighbridge.select_port());
		format_computed_weights(frm);
		if (frm.doc.docstatus === 0) {
			// the Fetch Weight button in the Weights tab takes the next missing weighing; these two take a
			// named one, so an operator can re-read just the loaded or just the empty vehicle
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
	slip_time: set_shift,
	after_save(frm) {
		format_computed_weights(frm);
	},
	on_hide(frm) {
		frm.page.wrapper.removeClass("wbs-slip");
	},
	fetch_weight(frm) {
		// the first reading is the loaded vehicle (gross), the next one the empty vehicle (tare)
		if (!flt(frm.doc.gross_weight)) return capture(frm, "gross_weight");
		if (!flt(frm.doc.tare_weight)) return capture(frm, "tare_weight");
		frappe.show_alert({ message: __("Loaded and Empty Vehicle Weights are already taken. Edit a weight to read it again."), indicator: "orange" });
	},
	gross_weight: calc,
	tare_weight: calc,
	mat_weight: calc,
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

// Same chain as WeighmentSlip.calculate_weights(); the server repeats it on save.
// It runs whenever any input changes, so typing only the Loaded Vehicle Weight already fills everything below it.
function calc(frm) {
	if (frm.doc.docstatus !== 0) return;
	const loaded = flt(frm.doc.gross_weight), empty = flt(frm.doc.tare_weight), binding = flt(frm.doc.mat_weight);
	const percent = Math.min(Math.max(flt(frm.doc.other_deduction_percent), 0), 100);
	const cane = loaded ? flt(loaded - empty, 2) : 0;
	const net_after_binding = flt(cane - binding, 2);
	const deduction = flt((net_after_binding * percent) / 100, 2);
	frm.set_value("cane_weight", cane);
	frm.set_value("net_after_binding", net_after_binding);
	frm.set_value("other_deduction", deduction);
	frm.set_value("net_cane_weight", flt(net_after_binding - deduction, 2));
	setTimeout(() => format_computed_weights(frm), 50);
}

// weight and capture time of each weighing; the scale must also agree with the weighing already taken
const WEIGHT_TIME_FIELD = { gross_weight: "gross_weight_time", tare_weight: "tare_weight_time" };

function capture(frm, field) {
	return vyavantra.weighbridge.capture(frm, field, WS_METHOD, {
		time_field: WEIGHT_TIME_FIELD[field],
		check: (weight) => {
			const loaded = flt(frm.doc.gross_weight), empty = flt(frm.doc.tare_weight);
			if (field === "tare_weight" && loaded && weight >= loaded) {
				return __("Scale shows {0} kg, but Loaded Vehicle Weight is {1} kg. Is the vehicle unloaded?", [weight, loaded]);
			}
			if (field === "gross_weight" && empty && weight <= empty) {
				return __("Scale shows {0} kg, but Empty Vehicle Weight is {1} kg. Is the vehicle loaded?", [weight, empty]);
			}
		},
	});
}

// weights tab layout: public/css/weighment_slip.css
const COMPUTED_WEIGHTS = ["cane_weight", "net_after_binding", "other_deduction", "net_cane_weight"];

// computed weights are read-only, which Frappe prints as a bare "0"; show them with two decimals like the inputs
function format_computed_weights(frm) {
	COMPUTED_WEIGHTS.forEach((name) => {
		const field = frm.fields_dict[name];
		if (field) field.$wrapper.find(".control-value").text(format_number(flt(frm.doc[name]), null, 2));
	});
}
