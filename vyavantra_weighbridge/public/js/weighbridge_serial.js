// Fetch Weight for the weighbridge slips.
//
// Weighbridge Settings > "Read weight from":
//   Server               the server asks the indicator (HTTP URL or the server's own serial port)
//   Browser Serial Port  this browser (Chrome / Edge, https or localhost) reads the COM port of the PC it runs on
//   Weighbridge Service  this browser asks the WeighbridgeService of the weighbridge PC. 127.0.0.1 is tried first;
//                        the URL in Weighbridge Settings is used only when that one does not answer
//
// vyavantra.weighbridge.read(server_method) resolves with the weight in Kg.

frappe.provide("vyavantra.weighbridge");

(function () {
	const CONFIG = "vyavantra_weighbridge.indicator.get_indicator_config";
	const READ_TIMEOUT_MS = 8000;
	// the service listens here on the weighbridge PC itself; 127.0.0.1 always means "the PC running this browser"
	const DEFAULT_SERVICE_URL = "http://127.0.0.1:8765/weight/stable";

	class WeighbridgeError extends Error {}

	// first number of a line, same rule as the server (indicator.py)
	function parse_weight(line) {
		const m = /-?\d+(?:\.\d+)?/.exec(line);
		return m ? parseFloat(m[0]) : null;
	}

	async function pick_port() {
		if (!("serial" in navigator)) {
			throw new WeighbridgeError(
				window.isSecureContext
					? __("This browser cannot read a COM port. Use Chrome or Edge.")
					: __("The COM port can only be read on a secure (https) page.")
			);
		}
		// a port the user already allowed on this site is reused without asking again
		const granted = await navigator.serial.getPorts();
		if (granted.length) return granted[0];
		try {
			return await navigator.serial.requestPort();
		} catch (e) {
			// the chooser was closed, or the PC has no COM port at all
			throw new WeighbridgeError(__("No COM port was selected. Press Fetch Weight again and choose the weighbridge port."));
		}
	}

	// the indicator streams a line every few hundred ms; the weight is accepted once it has been
	// the same for `need` readings in a row, so a truck that is still rocking is never captured
	async function collect(port, need) {
		const reader = port.readable.getReader();
		const decoder = new TextDecoder();
		const timer = setTimeout(() => reader.cancel().catch(() => {}), READ_TIMEOUT_MS);
		let buffer = "";
		let synced = false; // the first chunk usually starts in the middle of a line
		let last = null;
		let run = 0;
		let seen = null;
		try {
			while (true) {
				const { value, done } = await reader.read();
				if (done) break;
				buffer += decoder.decode(value, { stream: true });
				const parts = buffer.split(/[\r\n]+/);
				buffer = parts.pop();
				if (!synced) {
					if (!parts.length) continue;
					synced = true;
					parts.shift();
				}
				for (const line of parts) {
					const weight = parse_weight(line);
					if (weight === null) continue;
					seen = weight;
					run = weight === last ? run + 1 : 1;
					last = weight;
					if (run >= need) return weight;
				}
			}
		} finally {
			clearTimeout(timer);
			try {
				await reader.cancel();
			} catch (e) {
				/* already cancelled */
			}
			reader.releaseLock();
		}
		throw new WeighbridgeError(
			seen === null
				? __("No weight received from the indicator. Check the cable, the COM port and the baud rate.")
				: __("The weight is not stable ({0} Kg). Wait until the scale settles and try again.", [seen])
		);
	}

	async function read_serial(config) {
		const port = await pick_port();
		try {
			await port.open({
				baudRate: config.baud_rate,
				dataBits: config.data_bits,
				stopBits: config.stop_bits,
				parity: config.parity,
			});
		} catch (e) {
			throw new WeighbridgeError(__("Could not open the COM port: {0}", [e.message]));
		}
		frappe.dom.freeze(__("Reading weight..."));
		try {
			return await collect(port, config.stable_readings);
		} finally {
			frappe.dom.unfreeze();
			try {
				await port.close();
			} catch (e) {
				/* already closed */
			}
		}
	}

	// WeighbridgeService answers { ok, weight } or { ok: false, error, live }; fetch does not throw on 408 / 503,
	// so data.ok is always checked
	async function ask_service(url, timeout_ms) {
		const target = new URL(url);
		target.searchParams.set("timeoutMs", timeout_ms);
		const res = await fetch(target, { cache: "no-store" }); // throws only when the service is unreachable
		return res.json();
	}

	// The service normally sits on this PC. The URL in Weighbridge Settings is the fallback, for a service
	// that was moved to another port or machine; it is only tried when the default one does not answer.
	async function read_service(config) {
		const urls = [DEFAULT_SERVICE_URL];
		if (config.service_url && config.service_url !== DEFAULT_SERVICE_URL) urls.push(config.service_url);
		const timeout_ms = config.service_timeout_ms || 15000;

		frappe.dom.freeze(__("Waiting for stable weight..."));
		try {
			// a request that is simply unreachable moves on to the next address
			for (const url of urls) {
				let data;
				try {
					data = await ask_service(url, timeout_ms);
				} catch (e) {
					continue;
				}
				// the service answered: an unstable scale is its answer, not a reason to ask somewhere else
				if (!data.ok) {
					throw new WeighbridgeError(
						frappe.utils.escape_html(data.error || "") +
							(data.live != null ? `<br>${__("Current reading")}: ${flt(data.live)} kg` : "")
					);
				}
				return flt(data.weight);
			}
			throw new WeighbridgeError(
				__('Weighbridge service not reachable at {0}. Open this slip on the weighbridge PC and make sure "WeighbridgeService" is running.', [
					urls.join(" " + __("or") + " "),
				])
			);
		} finally {
			frappe.dom.unfreeze();
		}
	}

	vyavantra.weighbridge.read = async function (server_method) {
		const config = await frappe.call({ method: CONFIG }).then((r) => r.message || {});
		if (config.source === "Weighbridge Service") return read_service(config);
		if (config.source !== "Browser Serial Port") {
			return frappe
				.call({ method: server_method, freeze: true, freeze_message: __("Reading weight indicator...") })
				.then((r) => r.message);
		}
		return read_serial(config);
	};

	// Fetch Weight handler: puts the reading into `field`, explains a failure to the operator.
	// options (optional):
	//   check(weight)  returns a message to refuse the reading (the field is left unchanged), or nothing to accept it
	//   time_field     Datetime field that gets the capture time
	vyavantra.weighbridge.capture = function (frm, field, server_method, options) {
		options = options || {};
		return vyavantra.weighbridge
			.read(server_method)
			.then(async (weight) => {
				if (weight === undefined || weight === null) return;
				const refusal = options.check && options.check(weight);
				if (refusal) {
					frappe.msgprint({ title: __("Check vehicle"), message: refusal, indicator: "orange" });
					return;
				}
				await frm.set_value(field, weight);
				if (options.time_field && frm.fields_dict[options.time_field]) {
					await frm.set_value(options.time_field, frappe.datetime.now_datetime());
				}
			})
			.catch((e) => {
				if (e && e.message) frappe.msgprint({ title: __("Weight not read"), message: e.message, indicator: "red" });
			});
	};

	// "Select Weighbridge COM Port" in the form menu: forget the old port and ask for the right one
	vyavantra.weighbridge.select_port = async function () {
		if (!("serial" in navigator)) {
			frappe.msgprint(__("This browser cannot read a COM port. Use Chrome or Edge."));
			return;
		}
		const granted = await navigator.serial.getPorts();
		for (const port of granted) {
			if (port.forget) await port.forget();
		}
		try {
			await navigator.serial.requestPort();
			frappe.show_alert({ message: __("COM port saved for this browser"), indicator: "green" });
		} catch (e) {
			// the chooser was closed without a choice
		}
	};
})();
