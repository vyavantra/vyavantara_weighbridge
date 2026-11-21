// Shared "Desktop-App" card theme — same visual language as Weighment Slip
// (white rounded cards, blue gradient section headers, bold labels) applied to the
// other main transactional forms. Pure UI: it only adds a CSS class and a header
// strip above each section; it never reads or changes field values.

frappe.provide("vyavantra.weighbridge");

/**
 * @param {object} frm
 * @param {object} [icons] - optional {fieldname: "emoji"} map; a section without an
 *     entry gets a generic document icon. Pass {fieldname: null} to skip a section
 *     (leave it as a plain card with no header bar, e.g. one with no label).
 */
vyavantra.weighbridge.apply_card_theme = function (frm, icons = {}) {
	frm.page.wrapper.addClass("wbs-card-form");

	frm.$wrapper.find(".form-section[data-fieldname]").each(function () {
		const $section = $(this);
		const fieldname = $section.attr("data-fieldname");
		if (fieldname in icons && icons[fieldname] === null) return;
		if ($section.find("> .wbs-card-header").length) return; // already injected

		const $head = $section.find("> .section-head").first();
		const label = $head.length
			? $.trim($head.clone().find(".collapse-indicator").remove().end().text())
			: "";
		if (!label) return;

		const icon = icons[fieldname] || "📄";
		$section.prepend(
			`<div class="wbs-card-header"><span class="wbs-icon">${icon}</span> ${frappe.utils.escape_html(label)}</div>`
		);
	});
};
