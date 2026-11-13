// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

// Taluka and District belong to the village, so the operator picks the village and sees the other two
// fill in. The server repeats this on save, so a stale pair can never be stored.
frappe.ui.form.on("Cane Supplier", {
	village(frm) {
		if (!frm.doc.village) {
			frm.set_value({ taluka: "", district: "" });
			return;
		}

		frappe.db.get_value("Village Master", frm.doc.village, ["taluka", "district"]).then((r) => {
			const place = r.message || {};
			frm.set_value({ taluka: place.taluka || "", district: place.district || "" });
		});
	},
});
