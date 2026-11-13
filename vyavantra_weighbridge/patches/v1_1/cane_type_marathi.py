"""Weighment Slip: Cane Type now holds the four Marathi crop types (आडसाली, पूर्वहंगामी, सुरू, खोडवा).

Existing slips may still hold the two old English values. They are mapped as:
	Plant Cane (लागणीचा ऊस)  ->  सुरू      (ASSUMPTION: "Plant Cane" has no single equivalent among the new
	                                        types; आडसाली and पूर्वहंगामी are equally valid. Correct the map
	                                        below, or the affected slips by hand, if the factory means otherwise.)
	Ratoon Cane (खोडवा ऊस)   ->  खोडवा    (direct equivalent)
Idempotent: slips already on a new value are not touched.
"""

import frappe

OLD_TO_NEW = {
	"Plant Cane (लागणीचा ऊस)": "सुरू",
	"Ratoon Cane (खोडवा ऊस)": "खोडवा",
}


def execute():
	for old, new in OLD_TO_NEW.items():
		frappe.db.sql("update `tabWeighment Slip` set cane_type = %s where cane_type = %s", (new, old))
