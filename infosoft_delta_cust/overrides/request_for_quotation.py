from __future__ import annotations

import frappe
from erpnext.buying.doctype.request_for_quotation.request_for_quotation import RequestforQuotation
from frappe import _
from frappe.utils import cint

from infosoft_delta_cust.utils.email_utils import (
	get_default_sender_for_user,
	get_logged_in_user_email,
	parse_cc_emails,
	resolve_sender_email,
)


class CustomRequestforQuotation(RequestforQuotation):
	"""
	Custom Override for Request for Quotation:
	1. Prevents automatic email dispatch immediately on Submit (emails go out only when triggered)
	2. Sends RFQ email to Standard Suppliers (`self.suppliers`) and Prospective Suppliers (`self.custom_adhoc_suppliers`)
	3. Supports selectable `From Email` (`custom_sender_email` or `sender_email` param), defaulting to logged-in user's Outgoing Email Account
	4. Defaults Internal CC (`custom_internal_cc_emails`) to the logged-in user (comma-separated editable) with `expose_recipients="header"`
	5. Renders vendor-isolated PDF per supplier so competitors are never exposed on the PDF
	"""

	def before_validate(self):
		super().before_validate()
		if hasattr(self, "custom_sender_email") and not (self.custom_sender_email or "").strip():
			default_sender = get_default_sender_for_user()
			if default_sender:
				self.custom_sender_email = default_sender
		if hasattr(self, "custom_internal_cc_emails") and self.is_new() and not (self.custom_internal_cc_emails or "").strip():
			user_email = get_logged_in_user_email()
			if user_email:
				self.custom_internal_cc_emails = user_email

	def on_submit(self):
		self.db_set("status", "Submitted")
		for supplier in self.suppliers or []:
			supplier.email_sent = 0
			supplier.quote_status = "Pending"
			supplier.db_set(
				{"email_sent": 0, "quote_status": "Pending"},
				update_modified=False,
			)

	def _get_rfq_email_template(self) -> tuple[str, str]:
		template_name = (getattr(self, "email_template", None) or "").strip() or "ENQ TO SUPPLIER"
		template = None
		if frappe.db.exists("Email Template", template_name):
			template = frappe.db.get_value(
				"Email Template",
				template_name,
				["subject", "use_html", "response_html", "response"],
				as_dict=True,
			)

		template_body = ""
		if template:
			template_body = (
				template.get("response_html") if cint(template.get("use_html")) else template.get("response")
			) or template.get("response") or template.get("response_html") or ""

		subject = (template.get("subject") if template else "") or f"Request for Quotation - {self.name}"
		message = (
			template_body
			or (getattr(self, "message_for_supplier", None) or "").strip()
			or f"<p>Please find attached Request for Quotation <b>{self.name}</b>.</p>"
		)
		return subject, message

	def _build_supplier_pdf(self, supplier_id: str | None = None) -> list:
		try:
			rfq_render = frappe.get_doc(self.doctype, self.name)
			if supplier_id:
				rfq_render.vendor = supplier_id
				rfq_render.set(
					"suppliers",
					[sr for sr in (rfq_render.get("suppliers") or []) if sr.supplier == supplier_id],
				)
			else:
				rfq_render.vendor = ""
				rfq_render.set("suppliers", [])
			pdf_data = frappe.attach_print(self.doctype, self.name, file_name=self.name, doc=rfq_render)
			return [pdf_data] if pdf_data else []
		except Exception:
			try:
				pdf_fallback = frappe.attach_print(self.doctype, self.name, file_name=self.name, print_format=None)
				return [pdf_fallback] if pdf_fallback else []
			except Exception as e:
				frappe.log_error(f"Error generating RFQ PDF print for {self.name}: {e}")
				return []

	@frappe.whitelist()
	def send_supplier_emails(
		self,
		sender_email: str | None = None,
		cc_emails: str | None = None,
	) -> dict:
		if not (self.has_permission("email") or self.has_permission("write")):
			frappe.throw(_("Not permitted to send emails for this Request for Quotation."), frappe.PermissionError)

		if self.docstatus != 1:
			frappe.throw(_("Request for Quotation {0} must be submitted before sending emails.").format(self.name))

		sender = resolve_sender_email(sender_email, self)
		if sender and frappe.db.has_column("Request for Quotation", "custom_sender_email"):
			self.db_set("custom_sender_email", sender, update_modified=False)

		if cc_emails is not None:
			cc_raw = cc_emails
		else:
			cc_raw = (getattr(self, "custom_internal_cc_emails", None) or "").strip() or get_logged_in_user_email()

		if frappe.db.has_column("Request for Quotation", "custom_internal_cc_emails"):
			self.db_set("custom_internal_cc_emails", cc_raw.strip(), update_modified=False)

		default_subject, default_message = self._get_rfq_email_template()

		now_time = frappe.utils.now()
		current_user = frappe.session.user
		sent_count = 0
		sent_recipients: list[str] = []

		# 1. Dispatch to Standard Suppliers (self.suppliers)
		for rfq_supplier in self.suppliers or []:
			if hasattr(rfq_supplier, "send_email") and not cint(rfq_supplier.send_email):
				continue

			supp_email = (rfq_supplier.email_id or "").strip()
			if not supp_email:
				continue

			supp_name = rfq_supplier.supplier or rfq_supplier.supplier_name or "Supplier"
			context = {
				"doc": self,
				"name": self.name,
				"supplier": supp_name,
				"sales_order_number": getattr(self, "sales_order_number", "") or "",
			}

			try:
				subject = frappe.render_template(default_subject, context)
				message = frappe.render_template(default_message, context)
			except Exception:
				subject = default_subject
				message = default_message

			cc_for_row = parse_cc_emails(cc_raw, exclude_recipient=supp_email)
			attachments = self._build_supplier_pdf(rfq_supplier.supplier)

			try:
				frappe.sendmail(
					recipients=[supp_email],
					sender=sender,
					reply_to=sender,
					cc=list(cc_for_row) if cc_for_row else None,
					subject=subject,
					message=message,
					reference_doctype=self.doctype,
					reference_name=self.name,
					attachments=attachments,
					expose_recipients="header",
					add_unsubscribe_link=0,
				)
				rfq_supplier.email_sent = 1
				rfq_supplier.db_set("email_sent", 1, update_modified=False)
				if (
					frappe.db.has_column(rfq_supplier.doctype, "custom_added_on")
					and not rfq_supplier.get("custom_added_on")
				):
					rfq_supplier.db_set("custom_added_on", now_time, update_modified=False)
				sent_count += 1
				sent_recipients.append(supp_email)
			except Exception as e:
				frappe.log_error(f"Failed sending RFQ email to {supp_email}: {e}")

		# 2. Dispatch to Prospective / Ad-hoc Suppliers (self.custom_adhoc_suppliers)
		for adhoc_supplier in getattr(self, "custom_adhoc_suppliers", None) or []:
			adhoc_email = (adhoc_supplier.email_id or "").strip()
			if not adhoc_email:
				continue

			supp_name = adhoc_supplier.supplier_name or "Prospective Supplier"
			context = {
				"doc": self,
				"name": self.name,
				"supplier": supp_name,
				"sales_order_number": getattr(self, "sales_order_number", "") or "",
			}

			try:
				subject = frappe.render_template(default_subject, context)
				message = frappe.render_template(default_message, context)
			except Exception:
				subject = default_subject
				message = default_message

			cc_for_row = parse_cc_emails(cc_raw, exclude_recipient=adhoc_email)
			attachments = self._build_supplier_pdf(None)

			try:
				frappe.sendmail(
					recipients=[adhoc_email],
					sender=sender,
					reply_to=sender,
					cc=list(cc_for_row) if cc_for_row else None,
					subject=subject,
					message=message,
					reference_doctype=self.doctype,
					reference_name=self.name,
					attachments=attachments,
					expose_recipients="header",
					add_unsubscribe_link=0,
				)
				if frappe.db.has_column(adhoc_supplier.doctype, "email_sent"):
					adhoc_supplier.db_set("email_sent", 1, update_modified=False)
				if frappe.db.has_column(adhoc_supplier.doctype, "added_on") and not adhoc_supplier.get("added_on"):
					adhoc_supplier.db_set("added_on", now_time, update_modified=False)
				sent_count += 1
				sent_recipients.append(adhoc_email)
			except Exception as e:
				frappe.log_error(f"Failed sending RFQ email to prospective {adhoc_email}: {e}")

		# 3. Record parent audit fields if present on RFQ
		if sent_count > 0:
			for fld, val in [
				("custom_email_sent", 1),
				("custom_email_sent_on", now_time),
				("custom_email_sent_by", current_user),
				("custom_email_recipient", ", ".join(sent_recipients)),
			]:
				if frappe.db.has_column("Request for Quotation", fld):
					self.db_set(fld, val, update_modified=False)

			frappe.msgprint(
				_("RFQ emails successfully dispatched from {0} to {1} supplier(s).").format(sender or "default", sent_count)
			)
		else:
			frappe.msgprint(_("No valid supplier email addresses found to send."))

		return {
			"success": sent_count > 0,
			"sent_count": sent_count,
			"sender": sender,
			"sent_on": now_time,
		}

	def send_to_supplier(self):
		"""Route standard ERPNext `send_to_supplier` calls through our unified CC + sender dispatch."""
		return self.send_supplier_emails()

	def send_email(self, data, sender, subject, message, attachments):
		"""Fallback override if `send_email` is called directly by core ERPNext routines."""
		resolved_sender = resolve_sender_email(None, self) or sender
		cc_raw = (getattr(self, "custom_internal_cc_emails", None) or "").strip() or get_logged_in_user_email()
		cc_list = parse_cc_emails(cc_raw, exclude_recipient=data.email_id)

		frappe.sendmail(
			recipients=[data.email_id],
			sender=resolved_sender,
			reply_to=resolved_sender,
			cc=list(cc_list) if cc_list else None,
			subject=subject,
			message=message,
			reference_doctype=self.doctype,
			reference_name=self.name,
			attachments=attachments,
			expose_recipients="header",
			add_unsubscribe_link=0,
		)
		data.email_sent = 1
		frappe.msgprint(
			_("Email Sent to Supplier {0} with CC").format(
				getattr(data, "supplier", None) or getattr(data, "supplier_name", "Supplier")
			)
		)


@frappe.whitelist()
def send_supplier_emails(
	rfq_name: str,
	sender_email: str | None = None,
	cc_emails: str | None = None,
) -> dict:
	"""Override module-level ERPNext `send_supplier_emails` endpoint for Desk Tools button & API."""
	rfq = frappe.get_doc("Request for Quotation", rfq_name)
	return rfq.send_supplier_emails(sender_email=sender_email, cc_emails=cc_emails)
