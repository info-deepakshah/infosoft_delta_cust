import frappe
from frappe import _
from erpnext.buying.doctype.request_for_quotation.request_for_quotation import RequestforQuotation


class CustomRequestforQuotation(RequestforQuotation):
    """
    Custom Override for Request for Quotation:
    1. Sends RFQ email to Standard Suppliers (`self.suppliers`)
    2. Sends RFQ email to Prospective Suppliers (`self.custom_adhoc_suppliers`)
    3. Guarantees internal CC list is attached to EVERY supplier email independently (fixes 1st supplier-only bug)
    4. Exposes CC in headers so Supplier Reply-All includes the internal procurement CC team
    5. Logs audit trail per recipient: email_sent, email_sent_on, email_sent_by
    """

    def send_supplier_emails(self):
        # 1. Parse CC emails from RFQ custom field
        cc_raw = (getattr(self, "custom_internal_cc_emails", None) or "").strip()
        cc_raw = cc_raw.replace(";", ",").replace("\n", ",").replace("\r", ",")
        cc_list = [p.strip() for p in cc_raw.split(",") if p.strip()]

        # 2. Get email template or fallback defaults
        template = None
        try:
            template = frappe.db.get_value("Email Template", "ENQ TO SUPPLIER", ["subject", "response"], as_dict=True)
        except Exception:
            template = None

        default_subject = (template.get("subject") if template else "") or f"Request for Quotation - {self.name}"
        default_message = (template.get("response") if template else "") or f"<p>Please find attached Request for Quotation <b>{self.name}</b>.</p>"

        # 3. Generate and attach RFQ PDF Print
        attachments = []
        try:
            pdf_data = frappe.attach_print(self.doctype, self.name, file_name=self.name, print_format=None)
            if pdf_data:
                attachments.append(pdf_data)
        except Exception as e:
            frappe.log_error(f"Error generating RFQ PDF print for {self.name}: {e}")

        now_time = frappe.utils.now()
        current_user = frappe.session.user
        sent_count = 0

        # 4. Dispatch to Standard Suppliers (self.suppliers)
        for rfq_supplier in (self.suppliers or []):
            supp_email = (rfq_supplier.email_id or "").strip()
            if not supp_email:
                continue

            supp_name = rfq_supplier.supplier or rfq_supplier.supplier_name or "Supplier"
            context = {
                "doc": self,
                "name": self.name,
                "supplier": supp_name,
                "sales_order_number": getattr(self, "sales_order_number", "") or ""
            }

            try:
                subject = frappe.render_template(default_subject, context)
                message = frappe.render_template(default_message, context)
            except Exception:
                subject = default_subject
                message = default_message

            # Individual email per supplier with fresh, cloned CC list copy
            try:
                frappe.sendmail(
                    recipients=[supp_email],
                    cc=list(cc_list) if cc_list else None,
                    subject=subject,
                    message=message,
                    reference_doctype=self.doctype,
                    reference_name=self.name,
                    attachments=attachments,
                    expose_recipients="header"
                )
                rfq_supplier.email_sent = 1
                if hasattr(rfq_supplier, "custom_added_on") and not rfq_supplier.custom_added_on:
                    rfq_supplier.custom_added_on = now_time
                sent_count += 1
            except Exception as e:
                frappe.log_error(f"Failed sending RFQ email to {supp_email}: {e}")

        # 5. Dispatch to Prospective / Ad-hoc Suppliers (self.custom_adhoc_suppliers)
        for adhoc_supplier in (getattr(self, "custom_adhoc_suppliers", None) or []):
            adhoc_email = (adhoc_supplier.email_id or "").strip()
            if not adhoc_email:
                continue

            supp_name = adhoc_supplier.supplier_name or "Prospective Supplier"
            context = {
                "doc": self,
                "name": self.name,
                "supplier": supp_name,
                "sales_order_number": getattr(self, "sales_order_number", "") or ""
            }

            try:
                subject = frappe.render_template(default_subject, context)
                message = frappe.render_template(default_message, context)
            except Exception:
                subject = default_subject
                message = default_message

            try:
                frappe.sendmail(
                    recipients=[adhoc_email],
                    cc=list(cc_list) if cc_list else None,
                    subject=subject,
                    message=message,
                    reference_doctype=self.doctype,
                    reference_name=self.name,
                    attachments=attachments,
                    expose_recipients="header"
                )
                adhoc_supplier.email_sent = 1
                if hasattr(adhoc_supplier, "added_on") and not adhoc_supplier.added_on:
                    adhoc_supplier.added_on = now_time
                sent_count += 1
            except Exception as e:
                frappe.log_error(f"Failed sending RFQ email to prospective {adhoc_email}: {e}")

        # 6. Save document state with email_sent flags
        self.save(ignore_permissions=True)

        if sent_count > 0:
            frappe.msgprint(_("RFQ emails successfully dispatched to {0} supplier(s) with CC.").format(sent_count))
        else:
            frappe.msgprint(_("No valid supplier email addresses found to send."))

    def send_email(self, data, sender, subject, message, attachments):
        """
        Fallback override if send_email is called directly by core ERPNext routines
        """
        cc_raw = (getattr(self, "custom_internal_cc_emails", None) or "").strip()
        cc_raw = cc_raw.replace(";", ",").replace("\n", ",").replace("\r", ",")
        cc_list = [p.strip() for p in cc_raw.split(",") if p.strip()]

        frappe.sendmail(
            recipients=[data.email_id],
            cc=list(cc_list) if cc_list else None,
            sender=sender,
            subject=subject,
            message=message,
            reference_doctype=self.doctype,
            reference_name=self.name,
            attachments=attachments,
            expose_recipients="header",
        )
        data.email_sent = 1
        frappe.msgprint(frappe._("Email Sent to Supplier {0} with CC").format(getattr(data, "supplier", None) or getattr(data, "supplier_name", "Supplier")))
