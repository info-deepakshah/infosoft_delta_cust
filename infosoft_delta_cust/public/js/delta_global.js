/*
 * Global Navbar Workspace & Dashboard Shortcut Customization
 * Injected dynamically on Desk load/page change
 */
(function() {
    function init_sidebar_injection() {
        console.log("[Global Customization] Initializing sidebar check...");
        let attempts = 0;
        const interval = setInterval(function() {
            attempts++;
            
            const sidebar = document.querySelector('.standard-sidebar, .sidebar, .desk-sidebar, .layout-side, [class*="sidebar"]');
            const frappeReady = (typeof frappe !== 'undefined' && frappe.session && frappe.session.user);
            
            if (sidebar && frappeReady) {
                clearInterval(interval);
                console.log("[Global Customization] Sidebar & Frappe ready. Triggering render...");
                hotpatch_sidebar();
                render_global_dashboard_sidebar();
            }
            
            if (attempts > 20) {
                clearInterval(interval);
                const matchedElements = Array.from(document.querySelectorAll('[class*="sidebar"], [class*="layout-side"]')).map(el => {
                    return el.tagName + "." + Array.from(el.classList).join(".");
                });
                console.log("[Global Customization] Check timed out. Found elements:", matchedElements);
            }
        }, 500);
    }

    // Framework Hotpatch to prevent sidebar crash on custom/private workspaces missing parent pages
    function hotpatch_sidebar() {
        if (typeof frappe !== 'undefined' && frappe.ui && frappe.ui.Sidebar && !frappe.ui.Sidebar.prototype.is_hotpatched) {
            frappe.ui.Sidebar.prototype.is_hotpatched = true;
            
            const original_choose_app_name = frappe.ui.Sidebar.prototype.choose_app_name;
            frappe.ui.Sidebar.prototype.choose_app_name = function(workspace) {
                try {
                    let res = original_choose_app_name.apply(this, arguments);
                    if (res) return res;
                } catch (e) {
                    console.log("[Global Customization] Caught sidebar choose_app_name crash, applying 'erpnext' fallback context.");
                }
                return "erpnext"; // Fallback to avoid TypeError crash
            };
            console.log("[Global Customization] Successfully hotpatched Sidebar.choose_app_name!");
        }
    }

    function render_global_dashboard_sidebar() {
        if (document.getElementById('da-sidebar-dashboards-section')) {
            console.log("[Global Customization] Section already rendered, skipping.");
            return;
        }

        const sidebar = document.querySelector('.standard-sidebar, .sidebar, .desk-sidebar, .layout-side, [class*="sidebar"]');
        if (!sidebar) {
            console.log("[Global Customization] Sidebar element not found in DOM.");
            return;
        }

        const userEmail = frappe.session.user;
        console.log("[Global Customization] Logged in user:", userEmail);
        
        let workspaces = [];
        let dashboards = [];

        // Step 1: Fetch private Workspaces
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Workspace",
                filters: {
                    "public": 0
                },
                fields: ["name", "title", "owner"],
                limit_page_length: 100
            },
            callback: function(r1) {
                workspaces = r1.message || [];
                console.log("[Global Customization] Fetched workspaces:", workspaces);
                
                // Step 2: Fetch custom Dashboards
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Dashboard",
                        filters: {
                            "is_standard": 0
                        },
                        fields: ["name", "owner"],
                        limit_page_length: 100
                    },
                    callback: function(r2) {
                        dashboards = r2.message || [];
                        console.log("[Global Customization] Fetched dashboards:", dashboards);
                        build_sidebar_section(workspaces, dashboards);
                    }
                });
            }
        });

        function build_sidebar_section(workspaces, dashboards) {
            if (document.getElementById('da-sidebar-dashboards-section')) return;

            const userWorkspaces = workspaces.filter(w => {
                return w.name.includes(userEmail) || w.owner === userEmail;
            });

            const userDashboards = dashboards.filter(d => {
                return d.owner === userEmail;
            });

            console.log("[Global Customization] Matching Workspaces:", userWorkspaces);
            console.log("[Global Customization] Matching Dashboards:", userDashboards);

            if (userWorkspaces.length === 0 && userDashboards.length === 0) {
                console.log("[Global Customization] No matching private workspaces or dashboards for user, skipping render.");
                return;
            }

            const section = document.createElement('div');
            section.id = 'da-sidebar-dashboards-section';
            section.style.cssText = 'margin-top: 15px; border-top: 1px solid rgba(0,0,0,0.05); padding-top: 10px;';

            const title = document.createElement('div');
            title.style.cssText = 'padding: 6px 16px; font-size: 10px; font-weight: bold; text-transform: uppercase; color: #888; letter-spacing: 0.8px;';
            title.innerText = 'My Shortcuts';
            section.appendChild(title);

            // Add Workspace links (🏠)
            userWorkspaces.forEach(w => {
                let displayName = w.name.split('-' + userEmail)[0] || w.title || w.name;
                displayName = displayName.trim();

                const link = document.createElement('a');
                link.className = 'da-sidebar-item';
                link.style.cssText = 'display: flex; align-items: center; padding: 7px 16px; font-size: 12.5px; color: #444; text-decoration: none; transition: background 0.15s, color 0.15s; border-radius: 4px; margin: 2px 8px; cursor: pointer;';
                
                // Route to the actual rendered workspace page (e.g. /app/[workspace-name])
                link.href = `/app/${encodeURIComponent(w.name)}`;
                
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    frappe.set_route(w.name);
                });

                link.innerHTML = `
                    <span style="margin-right: 8px; font-size: 13px; display: flex; align-items: center; justify-content: center; width: 16px;">🏠</span>
                    <span style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${displayName}</span>
                `;
                section.appendChild(link);
            });

            // Add Dashboard links (📊)
            userDashboards.forEach(d => {
                const link = document.createElement('a');
                link.className = 'da-sidebar-item';
                link.style.cssText = 'display: flex; align-items: center; padding: 7px 16px; font-size: 12.5px; color: #444; text-decoration: none; transition: background 0.15s, color 0.15s; border-radius: 4px; margin: 2px 8px; cursor: pointer;';
                
                // Route to the dashboard view
                link.href = `/app/dashboard-view/${encodeURIComponent(d.name)}`;
                
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    frappe.set_route('dashboard-view', d.name);
                });

                link.innerHTML = `
                    <span style="margin-right: 8px; font-size: 13px; display: flex; align-items: center; justify-content: center; width: 16px;">📊</span>
                    <span style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${d.name}</span>
                `;
                section.appendChild(link);
            });

            // Re-query sidebar
            const currentSidebar = document.querySelector('.standard-sidebar, .sidebar, .desk-sidebar, .layout-side, [class*="sidebar"]');
            if (!currentSidebar) {
                console.log("[Global Customization] Active sidebar disappeared during API call.");
                return;
            }

            // Find the list container that holds all standard sidebar links (BOM, Work Order, Settings, etc.)
            const linksContainer = currentSidebar.querySelector('.sidebar-items, .sidebar-menu, [class*="sidebar-items"], [class*="sidebar-menu"]');
            if (linksContainer) {
                linksContainer.appendChild(section);
                console.log("[Global Customization] Successfully appended shortcuts section to links container!");
            } else {
                // Fallback: append before the user profile
                const userProfile = currentSidebar.querySelector('.user-menu, [class*="user-profile"], [class*="avatar"]');
                if (userProfile && userProfile.parentNode === currentSidebar) {
                    currentSidebar.insertBefore(section, userProfile);
                } else {
                    currentSidebar.appendChild(section);
                }
                console.log("[Global Customization] Appended shortcuts section to sidebar wrapper (fallback).");
            }

            if (!document.getElementById('da-sidebar-item-style')) {
                const style = document.createElement('style');
                style.id = 'da-sidebar-item-style';
                style.innerHTML = `
                    .da-sidebar-item:hover {
                        background-color: #f1f5f9 !important;
                        color: var(--primary) !important;
                    }
                `;
                document.head.appendChild(style);
            }
        }
    }

    // Bind listeners
    if (typeof frappe !== 'undefined') {
        $(document).ready(function() {
            init_sidebar_injection();
        });
        $(document).on('page-change', function() {
            init_sidebar_injection();
        });
    }
})();
