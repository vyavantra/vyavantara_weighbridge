// Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Weighment Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
		{ fieldname: "shift", label: __("Shift"), fieldtype: "Link", options: "Weighbridge Shift" },
		{ fieldname: "farmer", label: __("Cane Supplier"), fieldtype: "Link", options: "Cane Supplier" },
		{ fieldname: "village", label: __("Village"), fieldtype: "Link", options: "Village Master" },
		{ fieldname: "vehicle", label: __("Vehicle"), fieldtype: "Link", options: "Tractor Number" },
		{ fieldname: "contractor", label: __("Contractor"), fieldtype: "Link", options: "Contractor Master" },
		{ fieldname: "agent", label: __("Agent"), fieldtype: "Link", options: "Cane Agent" },
		{ fieldname: "delivery_type", label: __("Delivery Type"), fieldtype: "Link", options: "Delivery Type" },
		{ fieldname: "slip_no", label: __("Slip / Serial No."), fieldtype: "Data" },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "Submitted\nCancelled\nDraft\nAll", default: "Submitted" },
		{ fieldname: "group_by", label: __("Group By"), fieldtype: "Select", default: "None",
			options: "None\nDate\nShift\nVillage\nCane Supplier\nVehicle\nDelivery Type\nCane Rate\nDeduction Reason\nTransport Contractor\nCutting Contractor\nAgent" },
	],
};
