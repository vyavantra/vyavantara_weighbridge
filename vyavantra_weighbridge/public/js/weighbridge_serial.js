// Fetch Weight for the weighbridge slips.
//
// The weight indicator is read by the WeighbridgeService, a small Windows service running on the
// weighbridge PC. It holds the COM port open, decides when the weight is stable, and answers on
// http://127.0.0.1:8765. On a Fetch Weight click this script calls that address directly: the request
// never leaves the PC, and the cloud server is not involved until the slip is saved.
//
// 127.0.0.1 always means "the PC running this browser", so the ERP must be opened on the weighbridge PC.
//
// vyavantra.weighbridge.capture(frm, field, options) fills `field` with the stable weight.

frappe.provide("vyavantra.weighbridge");

(function () {
	const SERVICE_URL = "http://127.0.0.1:8765/weight/stable?timeoutMs=15000";

	// title and indicator travel with the message, so every failure keeps the service's own wording
	class WeighbridgeError extends Error {
		constructor(message, title, indicator) {
			super(message);
			this.title = title || __("Weight not read");
			this.indicator = indicator || "red";
		}
	}

	// The browser refuses to hand over a cross-origin response unless the service allows this exact ERP
	// address. A no-cors probe still succeeds in that case (the answer is opaque but the request arrives),
	// which separates "the service is not listening" from "the service is listening but rejects us".
	async function diagnose_unreachable() {
		try {
			await fetch(SERVICE_URL, { cache: "no-store", mode: "no-cors" });
		} catch (e) {
			return new WeighbridgeError(
				__('Open this slip on the weighbridge PC and make sure "WeighbridgeService" is running.'),
				__("Weighbridge service not reachable"),
				"red"
			);
		}
		return new WeighbridgeError(
			__("The service is running, but it does not accept requests from {0}.", [`<b>${frappe.utils.escape_html(window.location.origin)}</b>`]) +
				"<br><br>" +
				__("Add that address to AllowedOrigins in C:\\WeighbridgeService\\appsettings.json (no trailing slash) and restart the Weighbridge Service."),
			__("Weighbridge service rejected this site"),
			"red"
		);
	}

	// The service answers { ok: true, weight } or { ok: false, error, live }. fetch does not throw on
	// 408 (not stable) or 503 (COM port down), so data.ok is always checked; it throws only when the
	// response never arrives: service stopped, ERP open on another PC, or this site not allowed.
	async function read_service() {
		frappe.dom.freeze(__("Waiting for stable weight..."));
		try {
			let data;
			try {
				const res = await fetch(SERVICE_URL, { cache: "no-store" });
				data = await res.json();
			} catch (e) {
				throw await diagnose_unreachable();
			}
			if (!data.ok) {
				throw new WeighbridgeError(
					frappe.utils.escape_html(data.error || "") +
						(data.live != null ? `<br>${__("Current reading")}: ${flt(data.live)} kg` : ""),
					__("Weight not captured"),
					"orange"
				);
			}
			return flt(data.weight);
		} finally {
			frappe.dom.unfreeze();
		}
	}

	// Fetch Weight handler: puts the reading into `field`, explains a failure to the operator.
	// options (optional):
	//   transform(weight)  converts the reading before it is checked and stored, e.g. rounds it to whole kilograms
	//   check(weight)  returns a message to refuse the reading (the field is left unchanged), or nothing to accept it
	//   time_field     Datetime field that gets the capture time
	//   after(weight)  runs once the weight and its time are in the form, e.g. to save the slip
	vyavantra.weighbridge.capture = async function (frm, field, options) {
		options = options || {};
		const label = frm.fields_dict[field] ? __(frm.fields_dict[field].df.label) : field;
		try {
			let weight = await read_service();
			if (options.transform) weight = options.transform(weight);

			const refusal = options.check && options.check(weight);
			if (refusal) {
				frappe.msgprint({ title: __("Check vehicle"), message: refusal, indicator: "orange" });
				return;
			}

			await frm.set_value(field, weight);
			if (options.time_field && frm.fields_dict[options.time_field]) {
				await frm.set_value(options.time_field, frappe.datetime.now_datetime());
			}
			frappe.show_alert({ message: __("{0}: {1} kg", [label, weight]), indicator: "green" });
			if (options.after) await options.after(weight);
		} catch (e) {
			if (e && e.message) {
				frappe.msgprint({ title: e.title || __("Weight not read"), message: e.message, indicator: e.indicator || "red" });
			}
		}
	};
})();
