import frappe
from frappe import _
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder


class CustomPurchaseOrder(PurchaseOrder):
    """
    Custom Override for Purchase Order:
    - Dedicated method to dispatch PO email with internal CC header list
    - Guarantees CC visibility so supplier Reply-All includes the internal team
    - Attaches standard/configured Purchase Order PDF print format
    - Records comprehensive dispatch audit trail on the PO document
    """

    @frappe.whitelist()
    def send_po_email_with_cc(self, cc_emails=None):
        supplier_email = (
            self.contact_email
            or frappe.db.get_value("Supplier", self.supplier, "custom_communication_email")
            or frappe.db.get_value("Supplier", self.supplier, "email_id")
            or ""
        ).strip()

        if not supplier_email:
            frappe.throw(_("Supplier {0} has no valid communication email address on record.").format(self.supplier))

        # Parse CC emails (from parameter or PO custom field)
        cc_raw = cc_emails or (getattr(self, "custom_internal_cc_emails", None) or "").strip()
        cc_raw = cc_raw.replace(";", ",").replace("\n", ",").replace("\r", ",")
        cc_list = [p.strip() for p in cc_raw.split(",") if p.strip()]

        # Generate and attach PO PDF
        attachments = []
        try:
            pdf_data = frappe.attach_print(self.doctype, self.name, file_name=self.name, print_format=None)
            if pdf_data:
                attachments.append(pdf_data)
        except Exception as e:
            frappe.log_error(f"Error generating PO PDF print for {self.name}: {e}")

        # Render Subject & Message
        is_amended = bool(self.amended_from)
        rev_tag = f"[REVISED / AMENDED] " if is_amended else ""
        date_str = frappe.format_date(self.transaction_date) if self.transaction_date else ""
        subject = f"{rev_tag}Purchase Order {self.name} - Delta PD Pumps Private Limited"
        message = f"""
        <p>Dear <b>{self.supplier_name or self.supplier}</b>,</p>
        <p>Please find attached Purchase Order <b>{self.name}</b> dated <b>{date_str}</b>.</p>
        <p>Please acknowledge receipt and confirm acceptance along with the delivery schedule.</p>
        <br>
        <p>Best regards,<br><b>Purchase Department</b><br>Delta PD Pumps Private Limited</p>
        """

        # Dispatch email with isolated CC list copy
        frappe.sendmail(
            recipients=[supplier_email],
            cc=list(cc_list) if cc_list else None,
            subject=subject,
            message=message,
            reference_doctype=self.doctype,
            reference_name=self.name,
            attachments=attachments,
            expose_recipients="header",
        )

        # Audit logging (safe check for custom field existence)
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

        frappe.msgprint(_("Purchase Order {0} successfully emailed to {1} with CC.").format(self.name, supplier_email))
        return {"success": True, "recipient": supplier_email, "sent_on": now_time}
