# Copyright (c) 2026, Vyavantra Tech Solution PVT. LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

APPROVER_ROLES = {"Accounts Manager", "Weighbridge Manager", "System Manager"}
PARTY_NAME_FIELD = {
	"Farmer Bill": "farmer_name",
	"Tractor Contractor Bill": "contractor_name",
	"Todani Contractor Bill": "contractor_name",
	"Agent Bill": "agent_name",
}


class WeighbridgePayment(Document):
	def validate(self):
		bill = self.get_bill()
		self.party_name = bill.get(PARTY_NAME_FIELD[self.bill_doctype])
		self.bill_net_payable = bill.net_payable
		if self.docstatus == 0:
			self.outstanding_before = bill.outstanding_amount
			if flt(self.amount) > flt(bill.outstanding_amount):
				frappe.throw(
					_("Payment {0} exceeds the outstanding amount {1} of {2}").format(
						self.amount, bill.outstanding_amount, bill.name
					)
				)
		if flt(self.amount) <= 0:
			frappe.throw(_("Payment amount must be greater than zero"))
		if self.mode == "Cheque" and not (self.bank and self.cheque_no and self.cheque_date):
			frappe.throw(_("Bank, Cheque No. and Cheque Date are required for a cheque payment"))
		if self.mode == "Bank Transfer" and not self.bank:
			frappe.throw(_("Bank is required for a bank transfer"))
		self.validate_approval()

	def get_bill(self):
		bill = frappe.get_doc(self.bill_doctype, self.bill)
		if bill.docstatus != 1:
			frappe.throw(_("{0} {1} must be submitted before payment").format(self.bill_doctype, self.bill))
		return bill

	def validate_approval(self):
		before = self.get_doc_before_save()
		old = before.approval_status if before else "Pending"
		if self.approval_status != old:
			if not (APPROVER_ROLES & set(frappe.get_roles())):
				frappe.throw(_("Only an Accounts Manager or Weighbridge Manager can approve or reject a payment"))
			self.approved_by = frappe.session.user if self.approval_status != "Pending" else None

	def before_submit(self):
		if self.approval_status != "Approved":
			frappe.throw(_("Payment must be Approved before it can be submitted"))

	def on_submit(self):
		self.update_bill(flt(self.amount))

	def on_cancel(self):
		if self.reconciled:
			frappe.throw(_("This payment is bank reconciled and cannot be cancelled"))
		self.update_bill(-flt(self.amount))
		if self.journal_entry and frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus") == 1:
			frappe.get_doc("Journal Entry", self.journal_entry).cancel()

	def update_bill(self, amount):
		frappe.db.sql(f"select name from `tab{self.bill_doctype}` where name = %s for update", self.bill)
		frappe.get_doc(self.bill_doctype, self.bill).apply_payment(amount)


@frappe.whitelist()
def mark_reconciled(name, clearance_date=None):
	doc = frappe.get_doc("Weighbridge Payment", name)
	doc.check_permission("submit")
	if doc.docstatus != 1:
		frappe.throw(_("Only submitted payments can be reconciled"))
	if doc.mode == "Cash":
		frappe.throw(_("Cash payments do not need bank reconciliation"))
	doc.db_set({"reconciled": 1, "clearance_date": getdate(clearance_date or nowdate())})


@frappe.whitelist()
def make_journal_entry(name):
	"""Post the payment to accounts: Dr payable account, Cr cash / bank account."""
	doc = frappe.get_doc("Weighbridge Payment", name)
	doc.check_permission("submit")
	if doc.docstatus != 1:
		frappe.throw(_("Submit the payment first"))
	if doc.journal_entry:
		frappe.throw(_("Journal Entry {0} already exists").format(doc.journal_entry))
	s = frappe.get_doc("Weighbridge Settings")
	credit = s.cash_account if doc.mode == "Cash" else s.bank_account
	if not (s.company and s.payable_account and credit):
		frappe.throw(_("Set the Company, Payable Account and Cash / Bank Account in Weighbridge Settings first"))
	if frappe.db.get_value("Account", s.payable_account, "account_type") in ("Payable", "Receivable"):
		frappe.throw(
			_("Payable Account {0} is a Payable / Receivable type account, which needs a Party. "
			  "Choose an expense or liability account that is not party-linked in Weighbridge Settings.").format(
				s.payable_account
			)
		)
	ref_no = doc.cheque_no if doc.mode == "Cheque" else (doc.reference_no if doc.mode == "Bank Transfer" else None)
	je = frappe.new_doc("Journal Entry")
	je.update({
		"voucher_type": "Cash Entry" if doc.mode == "Cash" else "Bank Entry",
		"company": s.company,
		"posting_date": doc.payment_date,
		"cheque_no": ref_no,
		"cheque_date": (doc.cheque_date or doc.payment_date) if ref_no else None,
		"user_remark": _("{0} payment {1} against {2} {3} ({4})").format(
			doc.mode, doc.name, doc.bill_doctype, doc.bill, doc.party_name
		),
	})
	je.append("accounts", {"account": s.payable_account, "debit_in_account_currency": doc.amount})
	je.append("accounts", {"account": credit, "credit_in_account_currency": doc.amount})
	je.insert()
	je.submit()
	doc.db_set("journal_entry", je.name)
	return je.name
