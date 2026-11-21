// Slip Boy works in Desk: link pickers filter the active masters, and village/route selection
// behaves like the Weighment Slip. The linked weighment is created on submit, not on draft save.
const SBE_WS = "vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip.";

frappe.ui.form.on("Slip Boy Entry", {
	setup(frm) {
		frm.set_query("farmer", () => ({ filters: { disabled: 0 } }));
		frm.set_query("delivery_type", () => ({ filters: { disabled: 0 } }));
		frm.set_query("agent", () => ({ filters: { disabled: 0 } }));
		frm.set_query("transport_contractor", () => ({ filters: { contractor_type: ["in", ["Tractor Contractor", "Tractor / Cutting Contractor"]], disabled: 0 } }));
		frm.set_query("cutting_contractor", () => ({ filters: { contractor_type: ["in", ["Cutting Contractor", "Tractor / Cutting Contractor"]], disabled: 0 } }));
		frm.set_query("route", () => ({ query: SBE_WS + "route_query", filters: { village: frm.doc.village || "" } }));
	},
	refresh(frm) {
		frm.page.wrapper.addClass("wbs-mobile-form");
		vyavantra.weighbridge.apply_card_theme(frm, {
			sb_farmer_details: "👤",
			bank_details: "🏦",
			cane_details: "🌾",
			vehicle_details: "🚜",
		});
		if (frm.doc.docstatus === 1 && frm.doc.weighment_slip) {
			frm.add_custom_button(__("Open Weighment Slip"), () => frappe.set_route("Form", "Weighment Slip", frm.doc.weighment_slip));
		}
		add_mobile_action_bar(frm);
	},
	on_hide(frm) {
		frm.page.wrapper.removeClass("wbs-mobile-form");
	},
	farmer(frm) {
		if (frm.doc.farmer) {
			frm.set_value({ new_farmer_name: "", village: "", route: "" });
			frappe.db.get_value("Cane Supplier", frm.doc.farmer, "village").then((r) => {
				const village = (r.message && r.message.village) || "";
				load_routes(frm, village);
			});
		} else {
			load_routes(frm, frm.doc.village);
		}
	},
	village(frm) {
		if (!frm.doc.farmer) {
			load_routes(frm, frm.doc.village);
			load_taluka_state(frm, frm.doc.village);
		}
	},
});

// New Farmer section only: Village decides Taluka/District, District decides State — same chain
// Cane Supplier fills on its own form, shown here too so the slip boy sees it before submit.
function load_taluka_state(frm, village) {
	if (!village) {
		frm.set_value({ taluka: "", state: "" });
		return;
	}
	frappe.db.get_value("Village Master", village, ["taluka", "district"]).then((r) => {
		const place = r.message || {};
		frm.set_value("taluka", place.taluka || "");
		if (!place.district) {
			frm.set_value("state", "");
			return;
		}
		frappe.db.get_value("District Master", place.district, "state").then((r2) => {
			frm.set_value("state", (r2.message && r2.message.state) || "");
		});
	});
}

// Save / Submit also reachable at the bottom of the screen — the top toolbar's version of the
// same action is a thumb-stretch away on a phone, and is re-run on every refresh so it always
// matches the doc's current state (new/dirty -> Save, saved draft -> Submit, submitted -> gone).
function add_mobile_action_bar(frm) {
	frm.$wrapper.find(".wbs-mobile-action-bar").remove();
	if (frm.doc.docstatus === 1 || !frm.perm[0].write) return;

	const can_submit = frm.doc.docstatus === 0 && !frm.is_new() && !frm.is_dirty() && frm.perm[0].submit;
	const label = can_submit ? __("Submit") : __("Save");
	const $bar = $(`
		<div class="wbs-mobile-action-bar">
			<button type="button" class="btn btn-primary btn-block">${label}</button>
		</div>
	`);
	$bar.find("button").on("click", () => (can_submit ? frm.savesubmit() : frm.save()));
	frm.$wrapper.append($bar);
}

function load_routes(frm, village) {
	if (frm.doc.route) frm.set_value("route", "");
	if (!village) return;
	frappe.call({ method: SBE_WS + "get_village_routes", args: { village } }).then((r) => {
		const routes = r.message || [];
		if (routes.length === 1 && frm.doc.docstatus === 0) frm.set_value("route", routes[0].route);
	});
}
