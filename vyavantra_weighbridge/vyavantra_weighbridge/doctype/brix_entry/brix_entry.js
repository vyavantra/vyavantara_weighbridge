// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

const BRIX_MILL_FIELDS = ["mill_01", "mill_02", "mill_03", "mill_04"];
const BRIX_TIME_12 = "hh:mm A";
// what an operator may type: 2:35 PM, 02:35pm, 2.35 PM, 14:35 (same list as TYPED_FORMATS in brix_entry.py)
const BRIX_TYPED_FORMATS = ["h:mm A", "h:mmA", "h.mm A", "h.mmA", "h A", "hA", "H:mm", "H:mm:ss"];

frappe.ui.form.on("Brix Entry", {
	refresh(frm) {
		frm.page.wrapper.addClass("wbs-brix"); // scopes public/scss/_brix_entry.scss to this form

		const $page = frm.layout.wrapper.find(".form-page").first();
		if (!$page.find(".wbs-card-header").length) {
			$page.prepend(`<div class="wbs-card-header"><span class="wbs-icon">🧪</span> ${__("Brix Entry")}</div>`);
		}

		// phones open the number pad with a decimal point for the readings
		BRIX_MILL_FIELDS.forEach((name) => frm.fields_dict[name]?.$input?.attr("inputmode", "decimal"));

		// the time is stored on the 24 hour clock and shown on the 12 hour clock with AM / PM
		if (frm.doc.entry_time && frm.doc.docstatus === 0) {
			const shown = moment(frm.doc.entry_time, "HH:mm:ss").format(BRIX_TIME_12);
			if (frm.doc.entry_time_12 !== shown) {
				frm.doc.entry_time_12 = shown;
				frm.refresh_field("entry_time_12");
			}
		}

		if (frm.doc.docstatus === 0) inject_time_picker(frm);
	},
	entry_time_12(frm) {
		if (!frm.doc.entry_time_12) return;
		const typed = moment(frm.doc.entry_time_12.trim().toUpperCase(), BRIX_TYPED_FORMATS, true);
		if (!typed.isValid()) {
			frappe.show_alert({ message: __("Enter the time like 02:35 PM"), indicator: "orange" });
			return;
		}
		frm.set_value("entry_time", typed.format("HH:mm:ss"));
		const shown = typed.format(BRIX_TIME_12);
		if (frm.doc.entry_time_12 !== shown) frm.set_value("entry_time_12", shown);
	},
	on_hide(frm) {
		frm.page.wrapper.removeClass("wbs-brix");
	},
});

function inject_time_picker(frm) {
	const ctrl = frm.fields_dict["entry_time_12"];
	if (!ctrl) return;
	const $wrapper = ctrl.$wrapper;
	if ($wrapper.find(".wbs-time-picker-btn").length) return; // already injected

	// hidden native time input — only used to trigger the OS clock picker
	const $native = $('<input type="time" tabindex="-1" aria-hidden="true" class="wbs-time-native-input">');
	$wrapper.append($native);

	// clock button placed inside the input row
	const $btn = $('<button type="button" class="wbs-time-picker-btn" title="' + __("Pick time") + '">🕐</button>');
	$wrapper.find(".control-input-wrapper").addClass("wbs-time-input-row").append($btn);

	// sync current entry_time → native input so the picker opens at the right position
	const syncToNative = () => {
		if (frm.doc.entry_time) $native.val(frm.doc.entry_time.substring(0, 5));
	};

	$btn.on("click", () => {
		syncToNative();
		// showPicker() is the modern API; fall back to click() on older browsers
		if (typeof $native[0].showPicker === "function") {
			try { $native[0].showPicker(); } catch (_) { $native[0].click(); }
		} else {
			$native[0].click();
		}
	});

	// when the OS picker returns a value, push it into both fields
	$native.on("change", function () {
		const hhmm = this.value; // always "HH:MM" from <input type="time">
		if (!hhmm) return;
		const m = moment(hhmm, "HH:mm");
		frm.set_value("entry_time", m.format("HH:mm:ss"));
		frm.set_value("entry_time_12", m.format(BRIX_TIME_12));
	});
}
