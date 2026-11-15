// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

// the details that identify the load; without them a captured weight cannot be placed
const GWS_REQUIRED_BEFORE_WEIGHT = ["product_name", "vehicle_no", "party_name"];
const GWS_AUTO_SAVE_AFTER_FETCH = true;

frappe.ui.form.on("General Weighment Slip", {
	refresh(frm) {
		frm.page.wrapper.addClass("wbs-slip"); // scopes weighment_slip.css to this form only

		// ── Desktop-App Layout: show both tabs side-by-side ──
		show_side_by_side_layout(frm);
		inject_card_headers(frm);
		format_net_weight(frm);

		if (frm.doc.docstatus === 0) {
			set_fetch_label(frm);
			// each button reads its own weighing and asks before replacing one already taken
			frm.add_custom_button(__("Fetch Loaded Weight"), () =>
				capture_with_confirm(frm, "loaded_weight", __("Loaded Vehicle Weight"))
			).addClass("wbs-fetch-btn");
			frm.add_custom_button(__("Fetch Unloaded Weight"), () =>
				capture_with_confirm(frm, "empty_weight", __("Unloaded Vehicle Weight"))
			).addClass("wbs-fetch-btn");
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Print Slip"), () => frm.print_doc());
		}
	},
	on_hide(frm) {
		frm.page.wrapper.removeClass("wbs-slip");
	},
	after_save(frm) {
		set_fetch_label(frm);
		format_net_weight(frm);
	},
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
	setTimeout(() => format_net_weight(frm), 50);
}

// net weight is read-only, which Frappe prints as a bare "0"; show it with digit grouping and the unit
function format_net_weight(frm) {
	const field = frm.fields_dict.net_weight;
	if (!field) return;
	const value = flt(frm.doc.net_weight);
	const decimals = value % 1 ? 2 : 0;
	field.$wrapper.find(".control-value").text(format_number(value, null, decimals) + " Kg");
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

// ─── Desktop-App Layout Helpers (same design as Weighment Slip) ───────────────

/** Force both doctype tabs (Slip Details & Weighbridge) visible at the same time. */
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

async function capture_with_confirm(frm, field, label) {
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

	if (flt(frm.doc[field]) && !(await confirm_weight_replace(label, frm.doc[field]))) return;
	await capture(frm, field);
}

function confirm_weight_replace(label, existing_kg) {
	return new Promise((resolve) => {
		const d = new frappe.ui.Dialog({
			title: __("Replace Existing Weight?"),
			fields: [
				{
					fieldtype: "HTML",
					options: `<div style="padding:6px 0 10px;color:#344054;font-size:13px;line-height:1.6;">
						<p><b>${label}</b> ${__("is already recorded as")} <b>${format_number(existing_kg, null, 2)} Kg</b>.</p>
						<p>${__("Do you want to fetch a new reading from the scale and replace the current value?")}</p>
					</div>`,
				},
			],
			primary_action_label: __("Yes, Replace"),
			primary_action() {
				resolve(true);
				d.hide();
			},
			secondary_action_label: __("Cancel"),
			secondary_action() {
				d.hide();
			},
		});
		d.onhide = () => resolve(false); // a no-op after Yes, Replace has already resolved
		d.show();
	});
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
