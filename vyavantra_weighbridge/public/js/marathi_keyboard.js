// Marathi typing helper — a small popup (navbar button, or Alt+M).
//
// Primary way to type: type a word in English (or already in Marathi) in the "Type here" box;
// Devanagari suggestions appear below it (via Google's phonetic transliteration service, called
// through the server — see api.py — since that endpoint sends no CORS headers and so cannot be
// fetch()ed directly from the browser). Click the right one, or just press Space/Enter to accept
// the top suggestion and move to the next word.
//
// Fallback: a plain click-letter keyboard further down, for anything the suggestions don't cover.
//
// Either way, the result collects in "Composed text" at the top; Copy it and paste (Ctrl+V) it
// into whatever field you need, on any page.

frappe.provide("vyavantra.weighbridge");

const SUGGEST_METHOD = "vyavantra_weighbridge.api.marathi_suggestions";
const SUGGEST_DEBOUNCE_MS = 250;

const VOWELS = ["अ", "आ", "इ", "ई", "उ", "ऊ", "ऋ", "ए", "ऐ", "ओ", "औ", "अं", "अः", "ॲ", "ऑ"];
const MATRAS = ["ा", "ि", "ी", "ु", "ू", "ृ", "े", "ै", "ो", "ौ", "ं", "ः", "ँ", "्"];
const CONSONANT_ROWS = [
	["क", "ख", "ग", "घ", "ङ"],
	["च", "छ", "ज", "झ", "ञ"],
	["ट", "ठ", "ड", "ढ", "ण"],
	["त", "थ", "द", "ध", "न"],
	["प", "फ", "ब", "भ", "म"],
	["य", "र", "ल", "व"],
	["श", "ष", "स", "ह"],
	["ळ", "क्ष", "ज्ञ"],
];
const NUMERALS = ["०", "१", "२", "३", "४", "५", "६", "७", "८", "९", "।"];

// ─── Composed-text helpers ─────────────────────────────────────────────────

function insert_at_cursor($textarea, text) {
	const el = $textarea.get(0);
	const start = el.selectionStart ?? el.value.length;
	const end = el.selectionEnd ?? el.value.length;
	el.value = el.value.slice(0, start) + text + el.value.slice(end);
	const pos = start + text.length;
	el.focus();
	el.setSelectionRange(pos, pos);
}

function backspace_at_cursor($textarea) {
	const el = $textarea.get(0);
	const start = el.selectionStart ?? el.value.length;
	const end = el.selectionEnd ?? el.value.length;
	el.focus();
	if (start !== end) {
		el.value = el.value.slice(0, start) + el.value.slice(end);
		el.setSelectionRange(start, start);
		return;
	}
	if (!start) return;
	el.value = el.value.slice(0, start - 1) + el.value.slice(start);
	el.setSelectionRange(start - 1, start - 1);
}

// ─── Manual click-keyboard (fallback) ──────────────────────────────────────

function key_button(ch) {
	return `<button type="button" class="btn btn-default wbs-mrkey" data-ch="${ch}">${ch}</button>`;
}

function section(title, chars, css_class) {
	return `
		<div class="wbs-mrkey-section ${css_class}">
			<div class="wbs-mrkey-section-title">${title}</div>
			<div class="wbs-mrkey-grid">${chars.map(key_button).join("")}</div>
		</div>`;
}

function build_keyboard_html() {
	return `
		<div class="wbs-mrkeyboard">
			<div class="wbs-mrkey-section wbs-mrkey-special">
				<div class="wbs-mrkey-grid">
					<button type="button" class="btn btn-default wbs-mrkey wbs-mrkey-wide" data-action="space">${__("Space")}</button>
					<button type="button" class="btn btn-default wbs-mrkey wbs-mrkey-wide" data-action="backspace">⌫ ${__("Backspace")}</button>
				</div>
			</div>
			${section(__("Vowels"), VOWELS, "wbs-mrkey-vowels")}
			${section(__("Matras"), MATRAS, "wbs-mrkey-matras")}
			${section(__("Consonants"), CONSONANT_ROWS.flat(), "wbs-mrkey-consonants")}
			${section(__("Numbers"), NUMERALS, "wbs-mrkey-numbers")}
		</div>`;
}

// ─── Type + suggest ─────────────────────────────────────────────────────────

let suggest_timer = null;

function fetch_suggestions(word, callback) {
	clearTimeout(suggest_timer);
	if (!word || !/[A-Za-z]/.test(word)) return callback([]); // already Devanagari / punctuation only
	suggest_timer = setTimeout(() => {
		frappe
			.call({ method: SUGGEST_METHOD, args: { word }, freeze: false })
			.then((r) => callback(r.message || []))
			.catch(() => callback([]));
	}, SUGGEST_DEBOUNCE_MS);
}

// `english_word` (what was actually typed) is always offered too, as the last option, in case
// none of the Marathi suggestions are right and the word should stay in English (a name, an
// abbreviation, a code, ...).
function render_suggestions($box, suggestions, english_word, on_pick) {
	const all = suggestions.slice();
	if (english_word && !all.includes(english_word)) all.push(english_word);
	if (!all.length) {
		$box.empty().hide();
		return;
	}
	$box.empty().show();
	all.forEach((s) => {
		const is_english_fallback = s === english_word && !suggestions.includes(s);
		$(`<button type="button" class="btn btn-default wbs-mrsuggest${is_english_fallback ? " wbs-mrsuggest-en" : ""}">${s}</button>`)
			.on("click", () => on_pick(s))
			.appendTo($box);
	});
}

function setup_type_and_suggest(d) {
	const $type = d.fields_dict.type_box.$input;
	const $suggest_box = d.fields_dict.suggestions_html.$wrapper;
	let current_suggestions = [];

	function accept(word) {
		insert_at_cursor(d.fields_dict.text.$input, word + " ");
		$type.val("");
		current_suggestions = [];
		render_suggestions($suggest_box, [], "", accept);
		$type.focus();
	}

	$type.on("input", () => {
		const word = $type.val().trim();
		fetch_suggestions(word, (suggestions) => {
			current_suggestions = suggestions;
			render_suggestions($suggest_box, suggestions, word, accept);
		});
	});

	$type.on("keydown", (e) => {
		if (e.key !== " " && e.key !== "Enter") return;
		e.preventDefault();
		const word = $type.val().trim();
		if (!word) return;
		accept(current_suggestions.length ? current_suggestions[0] : word);
	});
}

// ─── Dialog ─────────────────────────────────────────────────────────────────

function open_marathi_keyboard() {
	const d = new frappe.ui.Dialog({
		title: __("Marathi Typing"),
		fields: [
			{ fieldname: "type_section", fieldtype: "HTML", options: `<div class="wbs-mrtype-heading">${__("Type in English, pick the Marathi word")}</div>` },
			{
				fieldname: "type_box",
				fieldtype: "Data",
			},
			{ fieldname: "suggestions_html", fieldtype: "HTML", options: '<div class="wbs-mrsuggest-box"></div>' },
			{ fieldname: "sb_compose", fieldtype: "Section Break", label: __("Composed text") },
			{ fieldname: "text", fieldtype: "Small Text" },
			{
				fieldname: "show_keyboard",
				fieldtype: "Check",
				label: __("Show manual click-keyboard"),
			},
			{
				fieldname: "keys_html",
				fieldtype: "HTML",
				options: `<div class="wbs-mrkeyboard-scroll">${build_keyboard_html()}</div>`,
				depends_on: "eval:doc.show_keyboard",
			},
		],
		primary_action_label: __("Copy"),
		primary_action() {
			const value = d.fields_dict.text.$input.val() || "";
			if (!value) {
				frappe.show_alert({ message: __("Nothing to copy yet"), indicator: "orange" });
				return;
			}
			frappe.utils.copy_to_clipboard(value);
			frappe.show_alert({ message: __("Copied — now paste it (Ctrl+V) into the field you need"), indicator: "green" });
		},
		secondary_action_label: __("Clear"),
		secondary_action() {
			d.fields_dict.text.$input.val("").focus();
		},
	});

	d.$wrapper.addClass("wbs-mrkeyboard-dialog");
	d.$wrapper.find(".wbs-mrkey").on("click", function () {
		const action = $(this).data("action");
		if (action === "backspace") return backspace_at_cursor(d.fields_dict.text.$input);
		if (action === "space") return insert_at_cursor(d.fields_dict.text.$input, " ");
		insert_at_cursor(d.fields_dict.text.$input, $(this).data("ch"));
	});

	setup_type_and_suggest(d);
	d.fields_dict.suggestions_html.$wrapper.hide();

	d.show();
	setTimeout(() => d.fields_dict.type_box.$input.focus(), 200);
}

vyavantra.weighbridge.open_marathi_keyboard = open_marathi_keyboard;

// ─── Navbar button + shortcut ──────────────────────────────────────────────

function add_marathi_keyboard_button() {
	if ($(".wbs-marathi-toggle").length) return;
	const $li = $(`
		<li class="nav-item wbs-marathi-toggle" title="${__("Marathi Typing (Alt+M)")}">
			<button class="btn-reset nav-link wbs-marathi-btn" type="button">
				<span class="wbs-marathi-label">मक</span>
			</button>
		</li>
	`);
	$li.on("click", open_marathi_keyboard);
	const $navbar_nav = $(".navbar-nav").last();
	const $divider = $navbar_nav.find(".vertical-bar").first();
	if ($divider.length) $divider.before($li);
	else $navbar_nav.prepend($li);
}

$(document).on("startup app_ready", add_marathi_keyboard_button);
setTimeout(add_marathi_keyboard_button, 1500);

$(document).on("keydown", (e) => {
	if (e.altKey && (e.key === "m" || e.key === "M")) {
		e.preventDefault();
		open_marathi_keyboard();
	}
});
