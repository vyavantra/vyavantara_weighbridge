const root = root_element.shadowRoot || root_element;
const host = root.querySelector(".wbd");
const esc = (s) => frappe.utils.escape_html(String(s == null ? "" : s));
const t3 = (v) => (v || 0).toLocaleString("en-IN", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
const money = (v) => "₹ " + (v || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });
const dmy = (d) => d.split("-").reverse().join("/");
const go = (...r) => frappe.set_route(...r);
const PAL = ["#2563eb", "#0f766e", "#d97706", "#7c3aed", "#db2777", "#475569"];

function kpi(icon, label, value, unit, sub, color, route) {
	return `<div class="card kpi" style="--c:${color}" data-route='${JSON.stringify(route)}'>
		<span class="ico">${icon}</span><div class="l">${label}</div>
		<div class="v">${value}<small>${unit || ""}</small></div><div class="s">${sub || "&nbsp;"}</div></div>`;
}

function head(title, status) {
	return `<div class="sec"><span class="line"></span><div class="sh"><b>${title}</b>${status ? `<em><i class="led"></i>${status}</em>` : ""}</div><span class="line r"></span></div>`;
}

function lineChart(trend) {
	const W = 640, H = 230, L = 44, R = 14, T = 14, B = 30;
	const max = Math.max(...trend.map((x) => x.tons), 1);
	const step = Math.pow(10, Math.floor(Math.log10(max)));
	const top = Math.ceil(max / step) * step;
	const x = (i) => L + (i * (W - L - R)) / (trend.length - 1);
	const y = (v) => T + (1 - v / top) * (H - T - B);
	const pts = trend.map((p, i) => [x(i), y(p.tons)]);
	const path = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
	const area = path + ` L${x(trend.length - 1).toFixed(1)} ${H - B} L${L} ${H - B} Z`;
	let grid = "";
	for (let g = 0; g <= 4; g++) {
		const v = (top * g) / 4, gy = y(v);
		grid += `<line x1="${L}" x2="${W - R}" y1="${gy}" y2="${gy}" class="gl"/><text x="${L - 6}" y="${gy + 3}" text-anchor="end" class="ax">${Math.round(v)}</text>`;
	}
	const xl = trend.map((p, i) => (i % 5 === 0 || i === trend.length - 1)
		? `<text x="${x(i)}" y="${H - 10}" text-anchor="middle" class="ax">${p.date.slice(8)}/${p.date.slice(5, 7)}</text>` : "").join("");
	const dots = trend.map((p, i) => `<circle cx="${pts[i][0]}" cy="${pts[i][1]}" r="${p.tons ? 3.2 : 0}" class="dot"><title>${dmy(p.date)} : ${t3(p.tons)} MT</title></circle>
		<circle cx="${pts[i][0]}" cy="${pts[i][1]}" r="9" fill="transparent"><title>${dmy(p.date)} : ${t3(p.tons)} MT</title></circle>`).join("");
	return `<svg viewBox="0 0 ${W} ${H}" class="svg" role="img" aria-label="Daily net cane line graph">
		<defs><linearGradient id="lg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2563eb" stop-opacity=".28"/><stop offset="1" stop-color="#2563eb" stop-opacity="0"/></linearGradient></defs>
		${grid}${xl}<path d="${area}" fill="url(#lg)"/><path d="${path}" class="ln"/>${dots}</svg>`;
}

function donut(items, fmt) {
	const total = items.reduce((a, i) => a + i.v, 0);
	if (!total) return '<div class="empty">No data yet</div>';
	const R = 54, C = 2 * Math.PI * R;
	let off = 0;
	const arcs = items.map((it, i) => {
		const len = (it.v / total) * C;
		const a = `<circle r="${R}" cx="70" cy="70" fill="none" stroke="${PAL[i % PAL.length]}" stroke-width="22"
			stroke-dasharray="${len.toFixed(2)} ${(C - len).toFixed(2)}" stroke-dashoffset="${(-off).toFixed(2)}" transform="rotate(-90 70 70)"><title>${esc(it.label)}: ${fmt(it.v)}</title></circle>`;
		off += len;
		return a;
	}).join("");
	const legend = items.map((it, i) => `<div class="lg"><i style="background:${PAL[i % PAL.length]}"></i><span class="n" title="${esc(it.label)}">${esc(it.label)}</span>
		<span class="q">${fmt(it.v)}</span><span class="p">${((it.v / total) * 100).toFixed(1)}%</span></div>`).join("");
	return `<div class="pie"><svg viewBox="0 0 140 140" class="donut" role="img"><circle r="${R}" cx="70" cy="70" fill="none" stroke="var(--line)" stroke-width="22"/>${arcs}
		<text x="70" y="66" text-anchor="middle" class="ct">Total</text><text x="70" y="82" text-anchor="middle" class="cv">${fmt(total)}</text></svg><div class="legend">${legend}</div></div>`;
}

function barRows(items, color) {
	if (!items.length) return '<div class="empty">No data yet</div>';
	const max = Math.max(...items.map((i) => i.tons), 0.001);
	return items.map((i) => `<div class="row"><span class="n" title="${esc(i.label)}">${esc(i.label)}</span>
		<span class="t"><i style="width:${(i.tons / max) * 100}%;--c:${color}"></i></span><span class="q">${t3(i.tons)}</span></div>`).join("");
}

function render(d) {
	const k = d.kpi, o = d.outstanding;
	const diff = k.yesterday_tons ? ((k.today_tons - k.yesterday_tons) / k.yesterday_tons) * 100 : null;
	const cmp = diff === null ? "No weighment yesterday"
		: `<span class="${diff >= 0 ? "up" : "down"}">${diff >= 0 ? "▲" : "▼"} ${Math.abs(diff).toFixed(1)}%</span> vs yesterday (${t3(k.yesterday_tons)} MT)`;
	const recent = d.recent.length ? `<table class="tbl"><thead><tr><th>Slip</th><th>Date</th><th>Vehicle</th><th>Supplier</th><th>Village</th><th class="r">Net (MT)</th></tr></thead><tbody>${
		d.recent.map((r) => `<tr><td><a data-slip="${esc(r.name)}">${esc(r.name)}</a></td><td>${esc(dmy(r.date))} ${esc(r.time)}</td>
		<td>${esc(r.vehicle)}</td><td>${esc(r.party)}</td><td>${esc(r.village)}</td><td class="r">${t3(r.tons)}</td></tr>`).join("")}</tbody></table>`
		: '<div class="empty">No weighment slips yet</div>';
	const total = o.farmer + o.tractor + o.todani + o.agent;
	const out = [{ label: "Farmer", v: o.farmer }, { label: "Tractor Contractor", v: o.tractor }, { label: "Todani Contractor", v: o.todani }, { label: "Agent", v: o.agent }].filter((i) => i.v > 0);
	const tn = (v) => t3(v) + " MT";

	host.innerHTML = `
	<div class="hero"><div><h2>${esc(d.company || "Weighbridge")} – Dashboard</h2>
		<p>Season from ${esc(dmy(d.season_start))} · Today ${esc(dmy(d.today))} · Submitted slips with net weight only</p></div>
		<div class="acts"><button class="btn solid" data-new="Weighment Slip">+ New Weighment Slip</button><button class="btn" data-refresh>↻ Refresh</button></div></div>
	${head("TODAY &amp; SEASON", "LIVE")}
	<div class="grid g4">
		${kpi("⚖", "Today's Net Cane", t3(k.today_tons), "MT", cmp, "#0f766e", ["List", "Weighment Slip"])}
		${kpi("🚜", "Today's Vehicle Trips", k.today_trips, "", "Submitted slips today", "#2563eb", ["List", "Weighment Slip"])}
		${kpi("▦", "Season Net Cane", t3(k.season_tons), "MT", k.season_trips + " trips this season", "#2563eb", ["List", "Weighment Slip"])}
		${kpi("✕", "Cancelled Slips", k.cancelled, "", "This season", "#b91c1c", ["query-report", "Cancelled Weighment Slips"])}
	</div>
	${head("ACCOUNTS", "OUTSTANDING")}
	<div class="grid g4">
		${kpi("₹", "Farmer Outstanding", money(o.farmer), "", "Submitted bills", "#d97706", ["List", "Farmer Bill"])}
		${kpi("₹", "Tractor Contractor", money(o.tractor), "", "Submitted bills", "#d97706", ["List", "Tractor Contractor Bill"])}
		${kpi("₹", "Todani Contractor", money(o.todani), "", "Submitted bills", "#d97706", ["List", "Todani Contractor Bill"])}
		${kpi("₹", "Agent Outstanding", money(o.agent), "", "Submitted bills", "#d97706", ["List", "Agent Bill"])}
	</div>
	<div class="grid g3">
		${kpi("⏳", "Payments Pending Approval", k.pending_payments, "", "Awaiting approval", "#d97706", ["List", "Weighbridge Payment"])}
		${kpi("✓", "Paid Today", money(k.paid_today), "", "Submitted payments", "#15803d", ["List", "Weighbridge Payment"])}
		${kpi("Σ", "Total Outstanding", money(total), "", "All four bill types", "#b91c1c", ["query-report", "Bill Outstanding Report"])}
	</div>
	${head("ANALYTICS", "CHARTS")}
	<div class="grid g2">
		<div class="card"><h3>Daily net cane – last 30 days (MT)</h3>${lineChart(d.trend)}</div>
		<div class="card"><h3>Season by delivery type (MT)</h3>${donut(d.delivery.map((i) => ({ label: i.label, v: i.tons })), tn)}</div>
	</div>
	<div class="grid g3b">
		<div class="card"><h3>Outstanding by party type</h3>${donut(out, money)}</div>
		<div class="card"><h3>Season by shift (MT)</h3>${donut(d.shifts.map((s) => ({ label: s.label, v: s.tons })), tn)}</div>
		<div class="card"><h3>Top villages this season (MT)</h3>${barRows(d.villages, "#d97706")}</div>
	</div>
	${head("ACTIVITY", "RECENT")}
	<div class="card"><h3>Recent weighment slips</h3>${recent}</div>
	${head("QUICK LINKS", "")}
	<div class="quick">
		<a data-route='["query-report","Shift Wise Report"]'>Shift Wise Report</a>
		<a data-route='["query-report","Datewise Report"]'>Datewise Report</a>
		<a data-route='["query-report","Datewise Crushing Report"]'>Datewise Crushing Report</a>
		<a data-route='["query-report","Weighment Register"]'>Weighment Register</a>
		<a data-route='["query-report","Payment Register"]'>Payment Register</a>
		<a data-route='["List","Farmer Bill"]'>Farmer Bills</a>
		<a data-route='["List","Weighbridge Payment"]'>Payments</a>
		<a data-route='["Workspaces","Vyavantra Weighbridge"]'>Vyavantra Weighbridge</a></div>`;

	host.querySelectorAll("[data-route]").forEach((el) => el.addEventListener("click", () => go(...JSON.parse(el.dataset.route))));
	host.querySelectorAll("[data-slip]").forEach((el) => el.addEventListener("click", () => go("Form", "Weighment Slip", el.dataset.slip)));
	host.querySelectorAll("[data-new]").forEach((el) => el.addEventListener("click", () => frappe.new_doc(el.dataset.new)));
	host.querySelectorAll("[data-refresh]").forEach((el) => el.addEventListener("click", load));
}

function load() {
	frappe.call({ method: "vyavantra_weighbridge.dashboard.get_dashboard_data" })
		.then((r) => render(r.message))
		.catch(() => { host.innerHTML = '<div class="card empty">Could not load the dashboard. You need read access to Weighment Slip.</div>'; });
}
load();
