frappe.query_reports["Datewise Report"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.get_today(), -30), reqd: 1 },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
	],
	onload(report) {
		load_heading(report);
	},
};

function load_heading(report) {
	frappe.call("vyavantra_weighbridge.report_utils.get_report_heading").then((r) => {
		report.wb_heading = r.message || {};
	});
}
