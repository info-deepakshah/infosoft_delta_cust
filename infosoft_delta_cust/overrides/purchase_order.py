from __future__ import annotations

import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
from frappe import _
from frappe.utils import escape_html

from infosoft_delta_cust.utils.email_utils import (
	get_default_purchase_sender,
	parse_cc_emails,
	resolve_sender_email,
)


class CustomPurchaseOrder(PurchaseOrder):
	"""
	Custom Override for Purchase Order:
	- Dedicated method to dispatch PO email with internal CC header list
	- Supports selectable `From Email` (`custom_sender_email` or `sender_email` param), defaulting to `purchase@...`
	- Guarantees CC visibility so supplier Reply-All includes the internal team
	- Attaches standard/configured Purchase Order PDF print format
	- Records comprehensive dispatch audit trail on the PO document
	"""

	def before_validate(self):
		super().before_validate()
		if hasattr(self, "custom_sender_email") and not (self.custom_sender_email or "").strip():
			default_sender = get_default_purchase_sender()
			if default_sender:
				self.custom_sender_email = default_sender

	@frappe.whitelist()
	def send_po_email_with_cc(
		self,
		cc_emails: str | None = None,
		sender_email: str | None = None,
	) -> dict:
		if not (self.has_permission("email") or self.has_permission("write")):
			frappe.throw(_("Not permitted to send emails for this Purchase Order."), frappe.PermissionError)

		if self.docstatus != 1:
			frappe.throw(_("Purchase Order {0} must be submitted before sending email.").format(self.name))

		custom_supp_email = (
			frappe.db.get_value("Supplier", self.supplier, "custom_communication_email")
			if frappe.db.has_column("Supplier", "custom_communication_email")
			else None
		)
		standard_supp_email = (
			frappe.db.get_value("Supplier", self.supplier, "email_id")
			if frappe.db.has_column("Supplier", "email_id")
			else None
		)
		supplier_email = (self.contact_email or custom_supp_email or standard_supp_email or "").strip()

		if not supplier_email:
			frappe.throw(
				_("Supplier {0} has no valid communication email address on record.").format(self.supplier)
			)

		sender = resolve_sender_email(sender_email, self)
		if sender_email and frappe.db.has_column("Purchase Order", "custom_sender_email"):
			self.db_set("custom_sender_email", sender or "", update_modified=False)

		cc_raw = (
			cc_emails
			if cc_emails is not None
			else (getattr(self, "custom_internal_cc_emails", None) or "")
		)
		if cc_emails is not None and frappe.db.has_column("Purchase Order", "custom_internal_cc_emails"):
			self.db_set("custom_internal_cc_emails", cc_raw.strip(), update_modified=False)

		cc_list = parse_cc_emails(cc_raw, exclude_recipient=supplier_email)

		attachments = []
		try:
			pdf_data = frappe.attach_print(self.doctype, self.name, file_name=self.name, print_format=None)
			if pdf_data:
				attachments.append(pdf_data)
		except Exception as e:
			frappe.log_error(f"Error generating PO PDF print for {self.name}: {e}")

		is_amended = bool(self.amended_from)
		rev_tag = "[REVISED / AMENDED] " if is_amended else ""
		date_str = frappe.format_date(self.transaction_date) if self.transaction_date else ""
		company_raw = self.company or "Delta PD Pumps Private Limited"
		company_html = escape_html(company_raw)
		supplier_html = escape_html(self.supplier_name or self.supplier or "Supplier")
		po_name_html = escape_html(self.name)

		subject = f"{rev_tag}Purchase Order {self.name} - {company_raw}"
		message = f"""
		<p>Dear <b>{supplier_html}</b>,</p>
		<p>Please find attached Purchase Order <b>{po_name_html}</b> dated <b>{escape_html(date_str)}</b>.</p>
		<p>Please acknowledge receipt and confirm acceptance along with the delivery schedule.</p>
		<br>
		<p>Best regards,<br><b>Purchase Department</b><br>{company_html}</p>
		"""

		frappe.sendmail(
			recipients=[supplier_email],
			sender=sender,
			cc=list(cc_list) if cc_list else None,
			subject=subject,
			message=message,
			reference_doctype=self.doctype,
			reference_name=self.name,
			attachments=attachments,
			expose_recipients="header",
			add_unsubscribe_link=0,
		)

		now_time = frappe.utils.now()
		current_user = frappe.session.user

		for fld, val in [
			("custom_email_sent", 1),
			("custom_email_sent_on", now_time),
			("custom_email_sent_by", current_user),
			("custom_email_recipient", supplier_email),
		]:
			if frappe.db.has_column("Purchase Order", fld):
				self.db_set(fld, val, update_modified=False)

		frappe.msgprint(
			_("Purchase Order {0} successfully emailed to {1} with CC.").format(self.name, supplier_email)
		)
		return {
			"success": True,
			"recipient": supplier_email,
			"sender": sender,
			"sent_on": now_time,
		}
