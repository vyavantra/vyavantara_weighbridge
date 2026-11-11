import frappe

# Weighbridge Settings no longer decides how the weight is read: Fetch Weight always asks the
# WeighbridgeService on the weighbridge PC. These single-doctype values are left over from the
# server / browser-COM-port options and are now dead.
OBSOLETE = (
	"indicator_source",
	"indicator_service_url",
	"indicator_service_timeout",
	"indicator_url",
	"indicator_serial_port",
	"indicator_baud_rate",
	"indicator_parity",
	"indicator_data_bits",
	"indicator_stop_bits",
	"indicator_stable_readings",
)


def execute():
	frappe.db.delete("Singles", {"doctype": "Weighbridge Settings", "field": ("in", OBSOLETE)})
	frappe.clear_cache(doctype="Weighbridge Settings")
