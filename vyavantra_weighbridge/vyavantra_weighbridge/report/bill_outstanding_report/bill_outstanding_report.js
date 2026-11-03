// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Bill Outstanding Report"] = {
	filters: [
		{ fieldname: "bill_type", label: __("Bill Type"), fieldtype: "Select", default: "All",
			options: "All\nFarmer\nTractor Contractor\nTodani Contractor\nAgent" },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
		{ fieldname: "party", label: __("Party No."), fieldtype: "Data", description: __("Farmer / Contractor / Agent number") },
		{ fieldname: "only_outstanding", label: __("Only Outstanding"), fieldtype: "Check", default: 1 },
	],
};
