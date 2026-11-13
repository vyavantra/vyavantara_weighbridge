// Slip Boy works in Desk: link pickers filter the active masters, and village/route selection
// behaves like the Weighment Slip. The linked weighment is created on submit, not on draft save.
const SBE_WS = "vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip.";

frappe.ui.form.on("Slip Boy Entry", {
	setup(frm) {
		frm.set_query("farmer", () => ({ filters: { disabled: 0 } }));
		frm.set_query("delivery_type", () => ({ filters: { disabled: 0 } }));
		frm.set_query("agent", () => ({ filters: { disabled: 0 } }));
		frm.set_query("transport_contractor", () => ({ filters: { contractor_type: ["in", ["Tractor", "Both"]], disabled: 0 } }));
		frm.set_query("cutting_contractor", () => ({ filters: { contractor_type: ["in", ["Cutting Contractor", "Both"]], disabled: 0 } }));
		frm.set_query("route", () => ({ query: SBE_WS + "route_query", filters: { village: frm.doc.village || "" } }));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.weighment_slip) {
			frm.add_custom_button(__("Open Weighment Slip"), () => frappe.set_route("Form", "Weighment Slip", frm.doc.weighment_slip));
		}
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
		if (!frm.doc.farmer) load_routes(frm, frm.doc.village);
	},
});

function load_routes(frm, village) {
	if (frm.doc.route) frm.set_value("route", "");
	if (!village) return;
	frappe.call({ method: SBE_WS + "get_village_routes", args: { village } }).then((r) => {
		const routes = r.message || [];
		if (routes.length === 1 && frm.doc.docstatus === 0) frm.set_value("route", routes[0].route);
	});
}
