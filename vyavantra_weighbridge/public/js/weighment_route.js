// Older weighment screens could leave a browser pointing at the former Marathi workspace name.
// The current workspace is Vyavantra Weighbridge; Frappe keeps the preferred breadcrumb per browser.
$(document).on("startup", () => {
	const old_workspace = "Weighbridge (वजनकाटा)";
	const current_workspace = "Vyavantra Weighbridge";
	const doctype = "Weighment Slip";

	if (frappe.breadcrumbs.get_doctype_module(doctype) === old_workspace) {
		frappe.breadcrumbs.set_doctype_module(doctype, current_workspace);
	}

	const old_path = `/app/${frappe.router.slug(old_workspace)}`;
	if (decodeURI(location.pathname) === old_path) {
		frappe.set_route("List", doctype, "List");
	}
});
