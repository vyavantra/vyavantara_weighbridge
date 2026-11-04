frappe.ready(function () {
	const WS = "vyavantra_weighbridge.vyavantra_weighbridge.doctype.weighment_slip.weighment_slip.";
	const form = frappe.web_form;
	const field = (name) => form.fields_dict[name];

	// ------------------------------------------------------------------ helpers
	const call = (method, args) => frappe.call({ method, args, type: "POST" }).then((r) => r.message);
	const insert = (doc) => call("frappe.client.insert", { doc });
	const find = (doctype, filters) =>
		call("frappe.client.get_value", { doctype, filters, fieldname: "name" }).then((m) => m && m.name);

	// A web form turns every Link into a plain dropdown that is filled once with all records, so the
	// filtering done on the desk form (enabled records only, contractor of the right type) is done here
	// by filling the dropdown from the same server query.
	const rows_of = (doctype, filters) =>
		call("frappe.desk.search.search_link", {
			doctype,
			txt: "",
			filters: filters || {},
			reference_doctype: "Weighment Slip",
			page_length: 500,
		}).then((rows) =>
			(rows || []).map((x) => ({ value: x.value, label: x.label || x.value, description: x.description }))
		);

	// ------------------------------------------------------------------ the dropdowns of the form
	// field -> [doctype, filters]
	const SOURCES = {
		farmer: ["Cane Supplier", { disabled: 0 }],
		agent: ["Cane Agent", { disabled: 0 }],
		delivery_type: ["Delivery Type", { disabled: 0 }],
		variety: ["Cane Variety", { disabled: 0 }],
		vehicle: ["Tractor Number", {}],
		transport_contractor: ["Contractor Master", { contractor_type: "Tractor", disabled: 0 }],
		cutting_contractor: ["Contractor Master", { contractor_type: "Cutting Contractor", disabled: 0 }],
	};
	const reload = (name) => rows_of(...SOURCES[name]).then((rows) => field(name).set_data(rows));
	Object.keys(SOURCES).forEach(reload);

	// a record that was just created is added to the dropdown first, because the dropdown only accepts its own values
	const pick = (name, value) =>
		reload(name).then(() => {
			form.set_value(name, value);
		});

	// ------------------------------------------------------------------ quick create dialogs
	// Every dialog resolves with the name of the record it created (or found) through `done(name)`.
	const f = (fieldname, label, fieldtype, extra) =>
		Object.assign({ fieldname, label: __(label), fieldtype: fieldtype || "Data" }, extra || {});

	// a dropdown inside a dialog, with its own "+ New" link
	const link = (fieldname, label, extra) => f(fieldname, label, "Autocomplete", Object.assign({ options: [] }, extra));

	function open_dialog(title, fields, submit, loaders) {
		const d = new frappe.ui.Dialog({
			title: __(title),
			fields,
			primary_action_label: __("Create"),
			primary_action(values) {
				const btn = d.get_primary_btn();
				btn.prop("disabled", true);
				Promise.resolve(submit(values, d))
					.then((name) => {
						if (name === undefined) return;
						d.hide();
					})
					.catch(() => {})
					.finally(() => btn.prop("disabled", false));
			},
		});
		d.show();
		Object.keys(loaders || {}).forEach((fieldname) => {
			const [doctype, filters, creator] = loaders[fieldname];
			const fill = () => rows_of(doctype, filters).then((rows) => d.fields_dict[fieldname].set_data(rows));
			fill();
			if (creator) {
				add_new_link(d.fields_dict[fieldname], () =>
					creator((name) => fill().then(() => d.set_value(fieldname, name)))
				);
			}
		});
		return d;
	}

	function add_new_link(control, handler) {
		const $label = control.$wrapper.find(".control-label").first();
		$("<a href='#' class='chit-new'></a>")
			.text("+ " + __("New"))
			.css({ marginLeft: "10px", fontWeight: 600 })
			.on("click", (e) => {
				e.preventDefault();
				handler();
			})
			.appendTo($label);
	}

	// master whose name is its key: use the record that already has that name instead of failing on a duplicate
	const insert_or_find = (doctype, key, value, doc) =>
		find(doctype, { name: value }).then((name) => name || insert(Object.assign({ doctype, [key]: value }, doc)).then((d) => d.name));

	function new_district(done) {
		open_dialog("New District", [f("district_name", "District Name", "Data", { reqd: 1 })], (v) =>
			insert_or_find("District Master", "district_name", v.district_name.trim()).then((n) => (done(n), n))
		);
	}

	function new_taluka(done) {
		open_dialog(
			"New Taluka",
			[f("taluka_name", "Taluka Name", "Data", { reqd: 1 }), link("district", "District", { reqd: 1 })],
			(v) =>
				insert_or_find("Taluka Master", "taluka_name", v.taluka_name.trim(), { district: v.district }).then(
					(n) => (done(n), n)
				),
			{ district: ["District Master", {}, new_district] }
		);
	}

	// Route Master is keyed by its name; the same route can be reused by many villages with its own distance and rate
	const ensure_route = (route_name, description) =>
		insert_or_find("Route Master", "route_name", route_name.trim(), description ? { description } : {});

	function new_village(done) {
		open_dialog(
			"New Village",
			[
				f("village_name", "Village Name", "Data", { reqd: 1 }),
				link("taluka", "Taluka"),
				f("sb_route", "First Route (optional)", "Section Break"),
				link("route_name", "Route", { ignore_validation: 1, description: __("Pick one or type a new route name") }),
				f("distance_km", "Distance (Km)", "Float"),
				f("transport_rate", "Rate (per Ton)", "Currency"),
			],
			(v) => {
				const any_route = v.route_name || v.distance_km || v.transport_rate;
				if (any_route && !(v.route_name && flt(v.distance_km) > 0 && v.transport_rate !== undefined && v.transport_rate !== "")) {
					frappe.msgprint(__("For the first route enter the route, a distance above zero and the rate"));
					return;
				}
				const make = (route) => {
					const doc = { doctype: "Village Master", village_name: v.village_name.trim(), taluka: v.taluka || undefined };
					if (route) doc.routes = [{ doctype: "Village Route", route, distance_km: v.distance_km, transport_rate: v.transport_rate }];
					return insert(doc).then((d) => (done(d.name), d.name));
				};
				return find("Village Master", { village_name: v.village_name.trim() }).then((existing) => {
					if (existing) {
						frappe.msgprint(__("Village {0} already exists, it is selected", [v.village_name]));
						done(existing);
						return existing;
					}
					return any_route ? ensure_route(v.route_name).then(make) : make();
				});
			},
			{ taluka: ["Taluka Master", {}, new_taluka], route_name: ["Route Master", {}, null] }
		);
	}

	function new_farmer(done) {
		const d = open_dialog(
			"New Farmer / Member",
			[
				f("farmer_name", "Farmer Name", "Data", { reqd: 1 }),
				f("phone", "Phone"),
				link("village", "Village", {
					change() {
						const village = d && d.get_value("village");
						if (!village) return;
						// the village already knows its taluka and district
						call("frappe.client.get_value", {
							doctype: "Village Master",
							filters: { name: village },
							fieldname: ["taluka", "district"],
						}).then((m) => {
							if (!m) return;
							if (m.taluka && !d.get_value("taluka")) d.set_value("taluka", m.taluka);
							if (m.district && !d.get_value("district")) d.set_value("district", m.district);
						});
					},
				}),
				link("taluka", "Taluka"),
				link("district", "District"),
				f("address", "Address", "Small Text"),
			],
			(v) =>
				insert({
					doctype: "Cane Supplier",
					farmer_name: v.farmer_name.trim(),
					phone: v.phone,
					village: v.village || undefined,
					taluka: v.taluka || undefined,
					district: v.district || undefined,
					address: v.address,
				}).then((doc) => (done(doc.name), doc.name)),
			{
				village: ["Village Master", {}, new_village],
				taluka: ["Taluka Master", {}, new_taluka],
				district: ["District Master", {}, new_district],
			}
		);
	}

	// a route of the member's village: the Route Master (reused or new) goes into the village's Routes table
	function new_route(done) {
		if (!current_village) {
			frappe.msgprint(__("Select the farmer / member first, the route is added to the member's village"));
			return;
		}
		open_dialog(
			"New Route for " + (form.get_value("village_name") || current_village),
			[
				link("route_name", "Route", { reqd: 1, ignore_validation: 1, description: __("Pick one or type a new route name") }),
				f("distance_km", "Distance (Km)", "Float", { reqd: 1 }),
				f("transport_rate", "Rate (per Ton)", "Currency", { reqd: 1 }),
			],
			(v) => {
				if (!(flt(v.distance_km) > 0)) {
					frappe.msgprint(__("Distance must be greater than zero"));
					return;
				}
				return ensure_route(v.route_name)
					.then((route) =>
						call("frappe.client.get", { doctype: "Village Master", name: current_village }).then((village) => {
							if ((village.routes || []).some((r) => r.route === route)) {
								frappe.msgprint(__("Route {0} is already defined for this village", [route]));
								return;
							}
							village.routes.push({
								doctype: "Village Route",
								route,
								distance_km: v.distance_km,
								transport_rate: v.transport_rate,
							});
							return call("frappe.client.save", { doc: village }).then(() => route);
						})
					)
					.then((route) => {
						if (!route) return;
						done(route);
						return route;
					});
			},
			{ route_name: ["Route Master", {}, null] }
		);
	}

	function new_tractor() {
		open_dialog("New Vehicle", [f("tractor_number", "Vehicle / Tractor Number", "Data", { reqd: 1 })], (v) => {
			const number = v.tractor_number.trim();
			return find("Tractor Number", { tractor_number: number }).then((existing) => {
				if (existing) frappe.msgprint(__("Vehicle {0} already exists, it is selected", [number]));
				return (existing ? Promise.resolve(existing) : insert({ doctype: "Tractor Number", tractor_number: number }).then((d) => d.name)).then(
					(name) => (pick("vehicle", name), name)
				);
			});
		});
	}

	const new_contractor = (fieldname, type) => () =>
		open_dialog(
			type === "Tractor" ? "New Transporting Contractor" : "New Cutting Contractor",
			[f("contractor_name", "Contractor Name", "Data", { reqd: 1 }), f("phone", "Phone")],
			(v) =>
				insert({ doctype: "Contractor Master", contractor_type: type, contractor_name: v.contractor_name.trim(), phone: v.phone }).then(
					(d) => (pick(fieldname, d.name), d.name)
				)
		);

	function new_agent() {
		open_dialog("New Agent", [f("agent_name", "Agent Name", "Data", { reqd: 1 }), f("phone", "Phone")], (v) =>
			insert({ doctype: "Cane Agent", agent_name: v.agent_name.trim(), phone: v.phone }).then((d) => (pick("agent", d.name), d.name))
		);
	}

	function new_variety() {
		open_dialog("New Cane Variety", [f("variety_name", "Variety", "Data", { reqd: 1 })], (v) =>
			insert_or_find("Cane Variety", "variety_name", v.variety_name.trim()).then((name) => (pick("variety", name), name))
		);
	}

	// ------------------------------------------------------------------ "+ New" next to each label
	add_new_link(field("farmer"), () => new_farmer((name) => pick("farmer", name)));
	add_new_link(field("route"), () => new_route((route) => load_routes(current_village, route)));
	add_new_link(field("variety"), new_variety);
	add_new_link(field("vehicle"), new_tractor);
	add_new_link(field("transport_contractor"), new_contractor("transport_contractor", "Tractor"));
	add_new_link(field("cutting_contractor"), new_contractor("cutting_contractor", "Cutting Contractor"));
	add_new_link(field("agent"), new_agent);

	// ------------------------------------------------------------------ the form itself
	// the slip date starts as today (a web form cannot use the DocType's "Today" default)
	form.set_value("slip_date", frappe.datetime.get_today());

	// only the routes defined in the member's village
	let current_village = "";
	field("route").set_data([]);

	function load_routes(village, select) {
		return call(WS + "get_village_routes", { village }).then((routes) => {
			routes = routes || [];
			field("route").set_data(
				routes.map((x) => ({
					value: x.route,
					label: x.route,
					description: `${x.distance_km} Km | Rs ${x.transport_rate} per Ton`,
				}))
			);
			// the slip needs a route whenever the village has any; a single route needs no choice
			form.set_df_property("route", "reqd", routes.length ? 1 : 0);
			if (select) form.set_value("route", select);
			else if (routes.length === 1) form.set_value("route", routes[0].route);
		});
	}

	form.on("farmer", (_field, farmer) => {
		current_village = "";
		form.set_value("route", "");
		form.set_value("farmer_name", "");
		form.set_value("village_name", "");
		form.set_df_property("route", "reqd", 0);
		field("route").set_data([]);
		if (!farmer) return;
		call("frappe.client.get_value", { doctype: "Cane Supplier", filters: { name: farmer }, fieldname: ["farmer_name", "village"] }).then((m) => {
			m = m || {};
			current_village = m.village || "";
			form.set_value("farmer_name", m.farmer_name || "");
			if (!current_village) return;
			call("frappe.client.get_value", { doctype: "Village Master", filters: { name: current_village }, fieldname: "village_name" }).then((v) =>
				form.set_value("village_name", (v || {}).village_name || current_village)
			);
			load_routes(current_village);
		});
	});

	// the success page shows the number of the slip that was just created
	const handle_success = form.handle_success.bind(form);
	form.handle_success = (data) => {
		handle_success(data);
		if (!data || !data.name) return;
		$(".success-message").html(
			__("Weighment Slip No.") + ": <b style='font-size: 1.6em'>" + frappe.utils.escape_html(data.name) + "</b>"
		);
	};
});
