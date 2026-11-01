// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Payment Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
		{ fieldname: "bill_doctype", label: __("Bill Type"), fieldtype: "Select",
			options: "\nFarmer Bill\nTractor Contractor Bill\nTodani Contractor Bill\nAgent Bill" },
		{ fieldname: "mode", label: __("Mode"), fieldtype: "Select", options: "\nCash\nCheque\nBank Transfer" },
		{ fieldname: "unreconciled", label: __("Pending Bank Reconciliation"), fieldtype: "Check" },
	],
};
