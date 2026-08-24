import frappe

# Primary ERPNext DocTypes to attach database-level Client Scripts
TARGET_DOCTYPES = [
    "Sales Order", "Quotation", "Purchase Order", "Sales Invoice", 
    "Payment Reconciliation", "Customer", "Item", "Purchase Receipt", 
    "Delivery Note", "Lead", "Opportunity", "Supplier", "Work Order", 
    "Stock Entry", "Journal Entry", "Payment Entry", "Purchase Invoice", 
    "Request for Quotation", "Supplier Quotation", "Material Request"
]

FULL_WIDTH_JS = """/*
 * Infosoft Delta Customization - Global Full-Width Form Layout (Frappe v16)
 * Direct database Client Script execution
 */
frappe.ui.form.on(cur_frm.doctype, {
    refresh: function(frm) {
        try {
            if (!document.getElementById('delta-full-width-style')) {
                const style = document.createElement('style');
                style.id = 'delta-full-width-style';
                style.innerHTML = `
                    html body .section-body,
                    html body .section-head,
                    html body .form-section .section-body,
                    html body .form-section .section-head,
                    html body div.section-body,
                    html body div.section-head,
                    .section-body,
                    .section-head,
                    .form-section .section-body,
                    .form-section .section-head,
                    div.section-body,
                    div.section-head {
                        max-width: 100% !important;
                        width: 100% !important;
                        margin-left: 0 !important;
                        margin-right: 0 !important;
                    }
                    .container, .container-fluid, .page-container, .page-body, .layout-main, .layout-main-section, .form-page, .form-layout, .form-section {
                        max-width: 100% !important;
                        width: 100% !important;
                        margin-left: 0 !important;
                        margin-right: 0 !important;
                    }
                `;
                (document.head || document.documentElement || document.body).appendChild(style);
            }

            // Direct DOM property enforcement for v16 dynamic rendering
            document.querySelectorAll('.section-body, .section-head, .form-section .section-body').forEach(function(el) {
                el.style.setProperty('max-width', '100%', 'important');
                el.style.setProperty('width', '100%', 'important');
                el.style.setProperty('margin-left', '0px', 'important');
                el.style.setProperty('margin-right', '0px', 'important');
            });
        } catch (e) {
            console.error('[Full Width Customization] Error enforcing layout:', e);
        }
    }
});
"""

def install_full_width_client_script():
    """
    Automatically creates or updates database Client Scripts for all main DocTypes during bench migrate.
    """
    for doctype in TARGET_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue

        script_name = f"Full Width Layout - {doctype}"
        try:
            if frappe.db.exists("Client Script", script_name):
                doc = frappe.get_doc("Client Script", script_name)
                doc.script = FULL_WIDTH_JS
                doc.enabled = 1
                doc.dt = doctype
                doc.view = "Form"
                doc.save(ignore_permissions=True)
            else:
                doc = frappe.get_doc({
                    "doctype": "Client Script",
                    "name": script_name,
                    "title": script_name,
                    "dt": doctype,
                    "view": "Form",
                    "enabled": 1,
                    "script": FULL_WIDTH_JS
                })
                doc.insert(ignore_permissions=True)
            print(f"[infosoft_delta_cust] Installed Client Script for {doctype}")
        except Exception as e:
            print(f"[infosoft_delta_cust] Error creating Client Script for {doctype}: {e}")

    frappe.db.commit()
    frappe.clear_cache()
