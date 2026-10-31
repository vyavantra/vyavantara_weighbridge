// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Agent Commission Report"] = {
	filters: [
		{ fieldname: "agent", label: __("Agent"), fieldtype: "Link", options: "Cane Agent" },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
	],
};
