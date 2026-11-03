frappe.query_reports["Shift Wise Report"] = {
	filters: [
		{ fieldname: "report_date", label: __("Report Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "season_start", label: __("Season Start (for To Date)"), fieldtype: "Date",
			description: __("Defaults to 1 October of the season") },
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
