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
		frm.set_query("transport_contractor", () => ({ filters: { contractor_type: ["in", ["Tractor Contractor", "Tractor / Cutting Contractor"]], disabled: 0 } }));
		frm.set_query("cutting_contractor", () => ({ filters: { contractor_type: ["in", ["Cutting Contractor", "Tractor / Cutting Contractor"]], disabled: 0 } }));
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

		// ── Desktop-App Layout: show both tabs side-by-side ──
		show_side_by_side_layout(frm);
		inject_card_headers(frm);

		format_computed_weights(frm);
		// clear any cached 12-hour helper text (we no longer show it)
		frm.set_df_property("slip_time", "description", "");
		if (frm.doc.docstatus === 0) {
			set_fetch_label(frm);
			if (!frm.is_new()) load_binding_percent(frm);
			// Direct toolbar buttons — blue primary style (.wbs-fetch-btn); each has a replace-confirmation
			const $load_btn = frm.add_custom_button(__("Load"), () => capture_with_confirm(frm, "gross_weight", __("Loaded Vehicle Weight")));
			$load_btn.addClass("wbs-fetch-btn");
			const $empty_btn = frm.add_custom_button(__("Unload"), () => capture_with_confirm(frm, "tare_weight", __("Unloaded Vehicle Weight")));
			$empty_btn.addClass("wbs-fetch-btn");
			if (frm.is_new()) {
				show_cane_rates(frm);
				set_shift(frm);
			}
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Print Slip"), () => frm.print_doc());
			show_diesel_pavti_buttons(frm);
		}
	},
	vehicle(frm) {
		if (!frm.doc.vehicle) return;
		// the Tractor contractor that owns this tractor number, if it has exactly one
		frappe.call({ method: WS_PATH + "get_tractor_contractor", args: { tractor: frm.doc.vehicle } }).then((r) => {
			if (r.message) frm.set_value("transport_contractor", r.message);
		});
	},
	transport_contractor(frm) {
		if (!frm.doc.transport_contractor || frm.doc.vehicle) return;
		// auto-fill vehicle from contractor's tractor list (only when vehicle not already set)
		frappe.call({ method: WS_PATH + "get_contractor_tractors", args: { contractor: frm.doc.transport_contractor } }).then((r) => {
			const tractors = r.message || [];
			if (tractors.length === 1) {
				frm.set_value("vehicle", tractors[0]);
			} else if (tractors.length > 1) {
				const d = new frappe.ui.Dialog({
					title: __("Select Tractor"),
					fields: [{
						fieldname: "tractor_number", fieldtype: "Select", label: __("Tractor Number"),
						options: tractors.join("\n"), reqd: 1,
					}],
					primary_action_label: __("Select"),
					primary_action(vals) {
						frm.set_value("vehicle", vals.tractor_number);
						d.hide();
					},
				});
				d.show();
			}
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
		frm.set_value("binding_deduction_percent", 0);
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
			frm.set_value("binding_deduction_percent", found ? flt(rates.binding_deduction_percent) : 0);
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

// Recheck the master when an existing draft opens: its percent must follow this slip date and delivery type.
function load_binding_percent(frm) {
	if (!frm.doc.delivery_type) return;
	frappe.call({
		method: WS_PATH + "get_cane_rates",
		args: { slip_date: frm.doc.slip_date, delivery_type: frm.doc.delivery_type },
		callback: (r) => {
			frm.set_value("binding_deduction_percent", flt((r.message || {}).binding_deduction_percent));
			calc(frm);
		},
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
	const binding = kg((cane * flt(frm.doc.binding_deduction_percent)) / 100);
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

// weights tab layout: public/scss/_weighment_slip.scss
const COMPUTED_WEIGHTS = ["cane_weight", "mat_weight", "net_after_binding", "other_deduction", "net_cane_weight"];

// computed weights are read-only, which Frappe prints as a bare "0"; show them as whole kilograms with digit grouping
function format_computed_weights(frm) {
	COMPUTED_WEIGHTS.forEach((name) => {
		const field = frm.fields_dict[name];
		if (field) field.$wrapper.find(".control-value").text(format_number(kg(frm.doc[name]), null, 0) + " Kg");
	});
}

// ─── Desktop-App Layout Helpers ───────────────────────────────────────────────

/** Force both doctype tabs (Field Slip & Weighbridge) visible at the same time. */
function show_side_by_side_layout(frm) {
	// Frappe renders Tab Break fields as separate .tab-pane panels and only shows the active one.
	// We override that: make every panel visible so CSS grid can place them side-by-side.
	const $panes = frm.$wrapper.find(".form-tab-content .tab-pane");
	$panes.addClass("show active").css({ display: "block", opacity: 1 });
}

/** Inject styled card headers into each tab panel (only once). */
function inject_card_headers(frm) {
	const map = {
		tab_slip:    { icon: "📋", title: __("Weighment Slip Details") },
		tab_weights: { icon: "⚖️", title: __("Weight Measurement") },
	};
	for (const [fieldname, cfg] of Object.entries(map)) {
		const $pane = frm.$wrapper.find(`[id$="${fieldname}"]`);
		if (!$pane.length || $pane.find(".wbs-card-header").length) continue;
		$pane.prepend(
			`<div class="wbs-card-header">
				<span class="wbs-icon">${cfg.icon}</span> ${cfg.title}
			</div>`
		);
	}
}

/**
 * Capture a weight, but first ask for confirmation when a value is already recorded.
 * "Fetch Loaded Weight" and "Fetch Unloaded Weight" toolbar buttons use this.
 */
async function capture_with_confirm(frm, field, label) {
	if (frm.doc.docstatus !== 0) return;

	// Require the identifying fields before accepting any weight
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

	// If a weight is already recorded, confirm before overwriting
	if (flt(frm.doc[field])) {
		const replace = await confirm_weight_replace(label, frm.doc[field]);
		if (!replace) return;
	}

	await capture(frm, field);
}

/** Show a confirmation dialog when the operator tries to overwrite an existing weight reading. */
function confirm_weight_replace(label, existing_kg) {
	return new Promise((resolve) => {
		const existing_fmt = format_number(existing_kg, null, 0);
		const d = new frappe.ui.Dialog({
			title: __("Replace Existing Weight?"),
			fields: [
				{
					fieldtype: "HTML",
					options: `<div style="padding:6px 0 10px;color:#344054;font-size:13px;line-height:1.6;">
						<p><b>${label}</b> ${__("is already recorded as")} <b>${existing_fmt} Kg</b>.</p>
						<p>${__("Do you want to fetch a new reading from the scale and replace the current value?")}</p>
					</div>`,
				},
			],
			primary_action_label: __("Yes, Replace"),
			primary_action() { resolve(true); d.hide(); },
			secondary_action_label: __("Cancel"),
			secondary_action() { d.hide(); resolve(false); },
		});
		d.onhide = () => resolve(false); // pressing × is treated as Cancel
		d.show();
	});
}


// ─── Diesel Issue Pavti ───────────────────────────────────────────────────────

const DIESEL_PATH = "vyavantra_weighbridge.vyavantra_weighbridge.doctype.diesel_issue_entry.diesel_issue_entry.";

// one diesel pavti per slip: offer to create it, or to open and print the one that exists
function show_diesel_pavti_buttons(frm) {
	frappe.call({ method: DIESEL_PATH + "get_for_weighment_slip", args: { weighment_slip: frm.doc.name } }).then((r) => {
		const entry = r.message;
		if (!entry) {
			frm.add_custom_button(__("Create Diesel Issue Pavti"), () => create_diesel_pavti(frm));
			return;
		}
		frm.add_custom_button(
			__("Diesel Pavti {0} ({1} L)", [entry.name, entry.disel_qty]),
			() => frappe.set_route("Form", "Diesel Issue Entry", entry.name)
		);
		frm.add_custom_button(__("Print Diesel Pavti"), () => print_diesel_pavti(entry.name));
	});
}

function print_diesel_pavti(name) {
	frappe.set_route("print", "Diesel Issue Entry", name);
}

function create_diesel_pavti(frm) {
	// the slip's own contractor and tractor are fixed; a slip without them has them chosen here
	const d = new frappe.ui.Dialog({
		title: __("Create Diesel Issue Pavti"),
		fields: [
			{ fieldname: "issue_date", fieldtype: "Date", label: __("Issue Date"), default: frm.doc.slip_date, read_only: 1 },
			{
				fieldname: "transport_contractor", fieldtype: "Link", options: "Contractor Master",
				label: __("Diesel Receiver Name (Transport Contractor)"), reqd: 1,
				default: frm.doc.transport_contractor, read_only: frm.doc.transport_contractor ? 1 : 0,
				get_query: () => ({ filters: { contractor_type: ["in", ["Tractor Contractor", "Tractor / Cutting Contractor"]], disabled: 0 } }),
			},
			{
				fieldname: "tractor_number", fieldtype: "Link", options: "Tractor Number", label: __("Tractor Number"), reqd: 1,
				default: frm.doc.vehicle, read_only: frm.doc.vehicle ? 1 : 0,
			},
			{ fieldname: "petrol_pump", fieldtype: "Link", options: "Petrol Pump", label: __("Petrol Pump Name"), reqd: 1 },
			{ fieldname: "diesel_qty", fieldtype: "Float", label: __("Diesel Qty (Litre)"), reqd: 1 },
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			if (flt(values.diesel_qty) <= 0) return frappe.msgprint(__("Diesel Qty must be greater than zero"));
			d.disable_primary_action();
			frappe
				.call({
					method: DIESEL_PATH + "create_from_weighment_slip",
					args: {
						weighment_slip: frm.doc.name, petrol_pump: values.petrol_pump, diesel_qty: values.diesel_qty,
						transport_contractor: values.transport_contractor, tractor_number: values.tractor_number,
					},
				})
				.then((r) => {
					d.hide();
					frm.reload_doc();
					frappe.confirm(
						__("Diesel Pavti {0} is created. Print it now?", [r.message]),
						() => print_diesel_pavti(r.message)
					);
				})
				.catch(() => d.enable_primary_action());
		},
	});
	d.show();
}
