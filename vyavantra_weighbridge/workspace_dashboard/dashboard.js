(function () {
	const root = root_element;
	const $ = (role) => root.querySelector('[data-role="' + role + '"]');

	// ── navigation ────────────────────────────────────────────────
	root.querySelectorAll("[data-kind]").forEach((el) => {
		const go = () => {
			const kind = el.getAttribute("data-kind");
			const target = el.getAttribute("data-target");
			if (kind === "new") {
				frappe.new_doc(target);
			} else if (kind === "drafts") {
				frappe.set_route("list", target, { docstatus: 0 });
			} else if (kind === "report") {
				const ref = el.getAttribute("data-ref-doctype");
				if (ref) {
					// matches frappe's own routing for is_query_report = 0 reports
					frappe.set_route(frappe.router.slug(ref), "view", "report", target);
				} else {
					frappe.set_route("query-report", target);
				}
			} else {
				frappe.set_route("list", target);
			}
		};
		el.addEventListener("click", go);
		// the stat tiles are divs, so give them the keyboard behaviour a button has
		if (el.tagName !== "BUTTON") {
			el.setAttribute("tabindex", "0");
			el.setAttribute("role", "link");
			el.addEventListener("keydown", (e) => {
				if (e.key === "Enter" || e.key === " ") {
					e.preventDefault();
					go();
				}
			});
		}
	});

	// ── hide what this user may not open ──────────────────────────
	// Runs twice: once straight away off frappe's own boot data, then again when the
	// server answers. The first pass matters - if the stats call ever fails, the page
	// must still not show a card the user has no business seeing.
	function applyPermissions(can) {
		if (!can) {
			const boot = (frappe.boot && frappe.boot.user && frappe.boot.user.can_read) || null;
			if (!boot) return;
			can = {};
			boot.forEach((dt) => { can[dt] = true; });
			// an unlisted doctype means "not readable" only because boot lists every
			// readable one, so flip the default for anything the page asks about
			root.querySelectorAll("[data-target], [data-needs]").forEach((el) => {
				const needs = el.getAttribute("data-needs");
				(needs ? needs.split("|") : [el.getAttribute("data-target")]).forEach((dt) => {
					if (dt && can[dt] === undefined) can[dt] = false;
				});
			});
		}
		const allowed = (el) => {
			const needs = el.getAttribute("data-needs");
			const list = needs
				? needs.split("|")
				: [el.getAttribute("data-target")];
			// a "needs" list means: show when ANY one of them is readable
			return list.some((dt) => can[dt] !== false);
		};

		root.querySelectorAll(".vwb-link, .vwb-stat, .vwb-new").forEach((el) => {
			if (!allowed(el)) el.hidden = true;
		});
		// a card with nothing left to show goes too
		root.querySelectorAll(".vwb-card").forEach((card) => {
			const live = card.querySelectorAll(".vwb-link:not([hidden])").length;
			if (!live) card.hidden = true;
		});
		// and if every tile went, drop the whole strip so there is no empty gap
		const stats = root.querySelector(".vwb-stats");
		if (stats && !stats.querySelectorAll(".vwb-stat:not([hidden])").length) {
			stats.hidden = true;
		}
	}

	// ── numbers ───────────────────────────────────────────────────
	const fmt = (n) => (n || 0).toLocaleString("en-IN");
	const tonnes = (kg) => {
		const t = (kg || 0) / 1000;
		if (!t) return "0";
		const dp = t < 100 ? 2 : 1;
		return t.toLocaleString("en-IN", { minimumFractionDigits: dp, maximumFractionDigits: dp });
	};
	const put = (role, text, isZero) => {
		const el = $(role);
		if (!el) return;
		el.textContent = text;
		el.classList.toggle("is-zero", !!isZero);
	};

	function sparkline(trend) {
		const svg = $("spark");
		if (!svg || !trend || !trend.length) return;
		const vals = trend.map((d) => d.kg || 0);
		const max = Math.max.apply(null, vals);
		const W = 120, H = 28, n = vals.length;
		if (!max) {
			svg.innerHTML = '<line x1="0" y1="' + (H - 2) + '" x2="' + W + '" y2="' + (H - 2) +
				'" stroke="#dfe5ec" stroke-width="1.5" stroke-linecap="round"/>';
			return;
		}
		const step = W / (n - 1);
		const pts = vals.map((v, i) => [i * step, H - 2 - (v / max) * (H - 6)]);
		const line = pts.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
		const area = "0," + H + " " + line + " " + W + "," + H;
		const last = pts[pts.length - 1];
		svg.innerHTML =
			'<polygon points="' + area + '" fill="rgba(13,122,62,0.13)"/>' +
			'<polyline points="' + line + '" fill="none" stroke="#0d7a3e" stroke-width="1.8" ' +
			'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>' +
			'<circle cx="' + last[0].toFixed(1) + '" cy="' + last[1].toFixed(1) + '" r="2.6" fill="#0d7a3e"/>';
	}

	applyPermissions(null); // immediate pass, before the server is asked anything

	frappe.call({ method: "vyavantra_weighbridge.api.workspace_stats" }).then((r) => {
		const s = (r && r.message) || {};
		applyPermissions(s.can_read);

		const d = frappe.datetime.str_to_obj(s.date || frappe.datetime.get_today());
		$("date").textContent = d.toLocaleDateString("en-IN", {
			weekday: "long", day: "numeric", month: "long", year: "numeric",
		});

		if (s.can_read_slips) {
			put("today_slips", fmt(s.today_slips), !s.today_slips);
			$("today_kg").textContent = s.today_slips
				? tonnes(s.today_kg) + " MT weighed"
				: "no slips yet today";
			put("month_kg", tonnes(s.month_kg) + " MT", !s.month_kg);
			$("month_slips").textContent = fmt(s.month_slips) + " slip" + (s.month_slips === 1 ? "" : "s");
			put("open_drafts", fmt(s.open_drafts), !s.open_drafts);
			sparkline(s.trend);
		}
		put("pending_bills", fmt(s.pending_bills), !s.pending_bills);
	}).catch(() => {
		// the figures are a bonus; the links must keep working without them
		root.querySelectorAll(".vwb-stat").forEach((el) => { el.hidden = true; });
		const strip = root.querySelector(".vwb-stats");
		if (strip) strip.hidden = true;
		const dt = $("date");
		if (dt) dt.textContent = "";
	});
})();
