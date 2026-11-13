"""The slip used to hold the trailer and how it was loaded in one field, e.g. "पुढचा ट्रेलर वरची वायर".

They are two separate questions, so the slip now has a Trailer (Trailer 1 / Trailer 2) and a Trolley
Type (वरची वायर / मधली वायर / खालची वायर / फुल भरलेला). This splits what is stored, otherwise the old
values are no longer valid options and the slips refuse to open.

पुढचा (front) is Trailer 1 and मागचा (rear) is Trailer 2. A row that named only the trailer, with no
wire, keeps an empty Trolley Type.
"""

import frappe

TRAILER = (("पुढचा", "Trailer 1"), ("मागचा", "Trailer 2"))
TROLLEY = ("वरची वायर", "मधली वायर", "खालची वायर")


def execute():
	if not frappe.db.has_column("Weighment Slip", "trailer"):
		return

	rows = frappe.db.sql(
		"""select name, trolley_type from `tabWeighment Slip`
		where ifnull(trolley_type, '') != '' and trolley_type like %s""",
		"%ट्रेलर%",  # only the old combined values name the trailer; a split one is just the wire
		as_dict=True,
	)
	for row in rows:
		old = row.trolley_type

		trailer = next((new for word, new in TRAILER if word in old), None)
		trolley = next((wire for wire in TROLLEY if wire in old), None)

		if not trailer:
			continue  # not one of the old combined values: left as it is

		frappe.db.set_value(
			"Weighment Slip",
			row.name,
			{"trailer": trailer, "trolley_type": trolley},
			update_modified=False,
		)

	frappe.db.commit()
