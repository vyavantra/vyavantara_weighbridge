// Size of the logo in the top-left corner, set in Weighbridge Settings (Logo Height / Width).
// public/css/vyavantra_weighbridge.css reads the two CSS variables set here.

frappe.provide("vyavantra.weighbridge");

vyavantra.weighbridge.apply_logo_size = function (size) {
	size = size || frappe.boot.weighbridge_logo || {};
	const root = document.documentElement.style;
	const height = size.height || 55;
	root.setProperty("--wb-logo-height", height + "px");
	root.setProperty("--wb-logo-width", size.width ? size.width + "px" : "auto");
	root.setProperty("--navbar-height", Math.max(height + 1, 56) + "px");
};

$(document).on("startup", () => vyavantra.weighbridge.apply_logo_size());
if (window.frappe && frappe.boot) vyavantra.weighbridge.apply_logo_size();

// the settings form shows the new size straight after Save
frappe.ui.form.on("Weighbridge Settings", {
	after_save(frm) {
		frappe.boot.weighbridge_logo = { height: frm.doc.logo_height, width: frm.doc.logo_width };
		vyavantra.weighbridge.apply_logo_size();
	},
});
