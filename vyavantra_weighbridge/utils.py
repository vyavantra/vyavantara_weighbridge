"""Jinja helpers for print formats."""

# 0-100 in Marathi. 1-60 and 70-98 follow the chart at shalusharma.com/2024/09/marathi-numbers-1-to-100.html.
# 61-68 (ष्ट spelling) and 99 (नव्व्याण्णव) differ from that chart and come from standard Marathi usage
# [INFERENCE, not checked against a source]. Have a Marathi speaker confirm before go-live.
_UNITS = (
	"शून्य एक दोन तीन चार पाच सहा सात आठ नऊ दहा अकरा बारा तेरा चौदा पंधरा सोळा सतरा अठरा एकोणवीस "
	"वीस एकवीस बावीस तेवीस चोवीस पंचवीस सव्वीस सत्तावीस अठ्ठावीस एकोणतीस "
	"तीस एकतीस बत्तीस तेहेतीस चौंतीस पस्तीस छत्तीस सडतीस अडतीस एकोणचाळीस "
	"चाळीस एक्केचाळीस बेचाळीस त्रेचाळीस चव्वेचाळीस पंचेचाळीस सेहेचाळीस सत्तेचाळीस अठ्ठेचाळीस एकोणपन्नास "
	"पन्नास एक्कावन्न बावन्न त्रेपन्न चोपन्न पंचावन्न छपन्न सत्तावन्न अठ्ठावन्न एकोणसाठ "
	"साठ एकसष्ट बासष्ट त्रेसष्ट चौसष्ट पासष्ट सहासष्ट सदुसष्ट अडुसष्ट एकोणसत्तर "
	"सत्तर एक्काहत्तर बाहत्तर त्र्याहत्तर चौऱ्याहत्तर पंच्याहत्तर शहात्तर सत्त्याहत्तर अठ्ठ्याहत्तर एकोणऐंशी "
	"ऐंशी एक्क्याऐंशी ब्याऐंशी त्र्याऐंशी चौऱ्याऐंशी पंच्याऐंशी शहाऐंशी सत्त्याऐंशी अठ्ठ्याऐंशी एकोणनव्वद "
	"नव्वद एक्क्याण्णव ब्याण्णव त्र्याण्णव चौऱ्याण्णव पंच्याण्णव शहाण्णव सत्त्याण्णव अठ्ठ्याण्णव नव्व्याण्णव "
	"शंभर"
).split()
assert len(_UNITS) == 101

# "शंभर" stands alone; in compounds it is "<n>शे" (दोनशे, तीनशे ...) and "एकशे" for one.
_HUNDREDS = {1: "एकशे", 2: "दोनशे", 3: "तीनशे", 4: "चारशे", 5: "पाचशे", 6: "सहाशे", 7: "सातशे", 8: "आठशे", 9: "नऊशे"}


def _below_1000(n: int) -> str:
	if n <= 100:
		return _UNITS[n]
	h, rest = divmod(n, 100)
	return _HUNDREDS[h] + (f" {_UNITS[rest]}" if rest else "")


def _integer_words(n: int) -> str:
	if n < 1000:
		return _below_1000(n)
	if n >= 100000:
		raise ValueError("marathi_number_words supports values below 1,00,000")
	th, rest = divmod(n, 1000)
	return f"{_UNITS[th]} हजार" + (f" {_below_1000(rest)}" if rest else "")


def marathi_number_words(value, unit: str = "") -> str:
	"""30 -> "तीस", 30.5 -> "तीस पूर्णांक पाच दशांश", 125 -> "एकशे पंचवीस".

	`unit` is appended as-is (for example "लिटर"). Up to 2 decimal places, below 1,00,000.
	"""
	if value in (None, ""):
		return ""
	number = round(abs(float(value)), 2)
	whole, hundredths = divmod(int(round(number * 100)), 100)
	words = _integer_words(whole)
	if hundredths:
		if hundredths % 10 == 0:
			words += f" पूर्णांक {_UNITS[hundredths // 10]} दशांश"
		else:
			words += f" पूर्णांक {_UNITS[hundredths]} शतांश"
	return f"{words} {unit}".strip()


def validate_indian_mobile(doc, method=None):
	"""Doc event: every phone field of the document must be a 10 digit Indian mobile number (optionally with +91 / 0).
	Frappe's own Phone check only limits the characters, so "1" would pass."""
	import re

	import frappe
	from frappe import _

	for df in doc.meta.get("fields", {"fieldtype": "Data", "options": "Phone"}):
		value = (doc.get(df.fieldname) or "").strip()
		if not value:
			continue
		digits = re.sub(r"[\s\-]", "", value)
		digits = re.sub(r"^(\+?91|0)(?=\d{10}$)", "", digits)
		if not re.fullmatch(r"[6-9]\d{9}", digits):
			frappe.throw(
				_("{0}: {1} is not a valid mobile number. Enter 10 digits starting with 6, 7, 8 or 9.").format(
					_(df.label), frappe.bold(value)
				),
				title=_("Invalid Phone Number"),
			)
		doc.set(df.fieldname, digits)


# (min, max, default) in px; 0 means "use the default" (width: automatic)
LOGO_LIMITS = {"logo_height": (20, 120, 55), "logo_width": (20, 400, 0)}


def logo_size():
	"""{"height": px, "width": px} of the top-left logo from Weighbridge Settings; width 0 = automatic."""
	import frappe
	from frappe.utils import cint

	values = frappe.db.get_singles_dict("Weighbridge Settings")
	out = {}
	for key, (low, high, default) in LOGO_LIMITS.items():
		v = cint(values.get(key))
		out[key.replace("logo_", "")] = min(max(v, low), high) if v else default
	return out


def boot_logo_size(bootinfo):
	bootinfo.weighbridge_logo = logo_size()
