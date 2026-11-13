// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

// A vehicle number is written in capitals. The server upper-cases it on save as well; this is so the
// operator sees MH11AB1234 while typing instead of being corrected afterwards.
frappe.ui.form.on("Tractor Number", {
	tractor_number(frm) {
		const typed = frm.doc.tractor_number;
		if (!typed) return;

		const upper = typed.toUpperCase();
		if (upper !== typed) frm.set_value("tractor_number", upper);
	},
});
