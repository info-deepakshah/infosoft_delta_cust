import frappe
from erpnext.buying.doctype.request_for_quotation.request_for_quotation import RequestForQuotation


class CustomRequestforQuotation(RequestForQuotation):
    def send_email(self, data, sender, subject, message, attachments):
        """
        Override ERPNext RFQ supplier email to include internal CC list from RFQ:
        - Field: custom_internal_cc_emails (comma-separated)
        - CC is visible in headers so supplier Reply-All includes CC recipients
        """

        # Parse CC emails from RFQ custom field
        cc_raw = (getattr(self, "custom_internal_cc_emails", None) or "").strip()
        cc_raw = cc_raw.replace(";", ",").replace("\n", ",").replace("\r", ",")

        cc_list = []
        if cc_raw:
            for part in cc_raw.split(","):
                email = (part or "").strip()
                if email and email not in cc_list:
                    cc_list.append(email)

        # Call the same core email creator, but add CC + expose headers
        from frappe.core.doctype.communication.email import make

        make(
            subject=subject,
            content=message,
            recipients=data.email_id,
            cc=cc_list or None,
            sender=sender,
            attachments=attachments,
            send_email=True,
            doctype=self.doctype,
            name=self.name,
            expose_recipients="header",
        )["name"]

        frappe.msgprint(frappe._("Email Sent to Supplier {0}").format(data.supplier))
