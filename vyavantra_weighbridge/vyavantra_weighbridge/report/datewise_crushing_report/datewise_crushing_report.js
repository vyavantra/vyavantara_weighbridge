frappe.query_reports["Datewise Crushing Report"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.get_today(), -7), reqd: 1 },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
	],
	onload(report) {
		load_heading(report);
	},
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.row_type && data.row_type !== "slip") value = "<b>" + value + "</b>";
		return value;
	},
};

function load_heading(report) {
	frappe.call("vyavantra_weighbridge.report_utils.get_report_heading").then((r) => {
		report.wb_heading = r.message || {};
	});
}
