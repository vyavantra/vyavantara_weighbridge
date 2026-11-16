"""Reset Contractor Master advance_balance to 0.

advance_balance previously stored the *outstanding* advance (amount yet to be recovered).
It now stores the *recovered* amount (accumulates as bills deduct advance).
Reset to 0 so the new logic starts clean; total_advance_given is the new source of truth.
"""

import frappe


def execute():
    frappe.db.sql("update `tabContractor Master` set advance_balance = 0 where advance_balance != 0")
    frappe.db.commit()
