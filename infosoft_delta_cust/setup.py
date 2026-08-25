import frappe

# Primary ERPNext DocTypes to attach database-level Client Scripts
TARGET_DOCTYPES = [
    "Sales Order", "Quotation", "Purchase Order", "Sales Invoice", 
    "Payment Reconciliation", "Customer", "Item", "Purchase Receipt", 
    "Delivery Note", "Lead", "Opportunity", "Supplier", "Work Order", 
    "Stock Entry", "Journal Entry", "Payment Entry", "Purchase Invoice", 
    "Request for Quotation", "Supplier Quotation", "Material Request"
]

FULL_WIDTH_JS = """/* Custom layout overrides disabled - Standard ERPNext v16 Desk layout active */"""

@frappe.whitelist()
def install_full_width_client_script():
    """
    Cleans up database Client Scripts during bench migrate to restore standard ERPNext layout.
    """
    for doctype in TARGET_DOCTYPES:
        script_name = f"Full Width Layout - {doctype}"
        try:
            if frappe.db.exists("Client Script", script_name):
                doc = frappe.get_doc("Client Script", script_name)
                doc.enabled = 0
                doc.script = "// Standard ERPNext layout restored"
                doc.save(ignore_permissions=True)
        except Exception as e:
            print(f"[infosoft_delta_cust] Error disabling Client Script for {doctype}: {e}")

    frappe.db.commit()
    frappe.clear_cache()
