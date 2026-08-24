import frappe

def install_full_width_client_script():
    """
    Automatically creates or updates the global full-width form Client Script
    directly inside Frappe's database during bench migrate / app installation.
    """
    script_name = "Global Full Width Form Layout V16"
    script_content = """/*
 * Infosoft Delta Customization - Global Full-Width Form Layout (Frappe v16)
 * Injected automatically via database Client Script
 */
frappe.ui.form.on('*', {
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

    try:
        if frappe.db.exists("Client Script", script_name):
            doc = frappe.get_doc("Client Script", script_name)
            doc.script = script_content
            doc.enabled = 1
            doc.dt = "*"
            doc.view = "Form"
            doc.save(ignore_permissions=True)
            print(f"[infosoft_delta_cust] Updated Client Script: {script_name}")
        else:
            doc = frappe.get_doc({
                "doctype": "Client Script",
                "name": script_name,
                "title": script_name,
                "dt": "*",
                "view": "Form",
                "enabled": 1,
                "script": script_content
            })
            doc.insert(ignore_permissions=True)
            print(f"[infosoft_delta_cust] Created Client Script: {script_name}")

        frappe.db.commit()
        frappe.clear_cache()
    except Exception as e:
        print(f"[infosoft_delta_cust] Error installing Client Script: {e}")
