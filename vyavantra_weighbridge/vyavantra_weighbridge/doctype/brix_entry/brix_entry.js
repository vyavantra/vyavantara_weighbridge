// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

const BRIX_MILL_FIELDS = ["mill_01", "mill_02", "mill_03", "mill_04"];

frappe.ui.form.on("Brix Entry", {
	refresh(frm) {
		frm.page.wrapper.addClass("wbs-brix"); // scopes public/scss/_brix_entry.scss to this form

		const $page = frm.layout.wrapper.find(".form-page").first();
		if (!$page.find(".wbs-card-header").length) {
			$page.prepend(`<div class="wbs-card-header"><span class="wbs-icon">🧪</span> ${__("Brix Entry")}</div>`);
		}

		// phones open the number pad with a decimal point for the readings
		BRIX_MILL_FIELDS.forEach((name) => frm.fields_dict[name]?.$input?.attr("inputmode", "decimal"));
	},
	on_hide(frm) {
		frm.page.wrapper.removeClass("wbs-brix");
	},
});
