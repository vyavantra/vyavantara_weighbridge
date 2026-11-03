// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Cancelled Weighment Slips"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_months(frappe.datetime.get_today(), -1) },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
		{ fieldname: "farmer", label: __("Cane Supplier"), fieldtype: "Link", options: "Cane Supplier" },
		{ fieldname: "village", label: __("Village"), fieldtype: "Link", options: "Village Master" },
		{ fieldname: "vehicle", label: __("Vehicle"), fieldtype: "Link", options: "Tractor Number" },
		{ fieldname: "slip_no", label: __("Slip / Serial No."), fieldtype: "Data" },
	],
};
