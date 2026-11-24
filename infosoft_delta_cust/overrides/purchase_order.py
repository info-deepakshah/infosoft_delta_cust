from __future__ import annotations

import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
from frappe import _
from frappe.utils import escape_html

from infosoft_delta_cust.utils.email_utils import (
	get_logged_in_user_email,
	parse_cc_emails,
	resolve_sender_email,
)


class CustomPurchaseOrder(PurchaseOrder):
	"""
	Custom Override for Purchase Order:
	- Does NOT mutate or clutter PO DocType form on save (`before_validate` untouched)
	- Provides `send_po_email_with_cc` helper if invoked programmatically/from POD3,
	  defaulting `From Email` and `CC` to the logged-in user (Option 1).
	"""

	@frappe.whitelist()
	def send_po_email_with_cc(
		self,
		cc_emails: str | None = None,
		sender_email: str | None = None,
		recipient_email: str | None = None,
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
		supplier_email = (
			(recipient_email or "").strip()
			or (self.contact_email or "").strip()
			or (custom_supp_email or "").strip()
			or (standard_supp_email or "").strip()
		)

		if not supplier_email:
			frappe.throw(
				_("Supplier {0} has no valid communication email address on record.").format(self.supplier)
			)

		sender = resolve_sender_email(sender_email, self)
		if sender and frappe.db.has_column("Purchase Order", "custom_sender_email"):
			self.db_set("custom_sender_email", sender, update_modified=False)

		if cc_emails is not None:
			cc_raw = cc_emails
		else:
			cc_raw = (getattr(self, "custom_internal_cc_emails", None) or "").strip() or get_logged_in_user_email()

		if frappe.db.has_column("Purchase Order", "custom_internal_cc_emails"):
			self.db_set("custom_internal_cc_emails", cc_raw.strip(), update_modified=False)

		recipients_list = parse_cc_emails(supplier_email)
		if not recipients_list:
			frappe.throw(_("Invalid Supplier Recipient Email: {0}").format(supplier_email))

		cc_list = parse_cc_emails(cc_raw)
		recip_low_set = {e.lower() for e in recipients_list}
		cc_list = [c for c in cc_list if c.lower() not in recip_low_set]

		print_format = "PO - Domestic" if frappe.db.exists("Print Format", "PO - Domestic") else None
		attachments = []
		try:
			pdf_data = frappe.attach_print(self.doctype, self.name, file_name=self.name, print_format=print_format)
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
			recipients=recipients_list,
			sender=sender,
			reply_to=sender,
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
		recip_str = ", ".join(recipients_list)

		for fld, val in [
			("custom_email_sent", 1),
			("custom_email_sent_on", now_time),
			("custom_email_sent_by", current_user),
			("custom_email_recipient", recip_str),
		]:
			if frappe.db.has_column("Purchase Order", fld):
				self.db_set(fld, val, update_modified=False)

		frappe.msgprint(
			_("Purchase Order {0} successfully emailed from {1} to {2}.").format(self.name, sender or "default", recip_str)
		)
		return {
			"success": True,
			"recipient": recip_str,
			"sender": sender,
			"sent_on": now_time,
		}
