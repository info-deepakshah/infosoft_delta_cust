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
            
            const sidebar = document.querySelector('.desk-sidebar, .layout-side, .sidebar-left, .standard-sidebar');
            const frappeReady = (typeof frappe !== 'undefined' && frappe.session && frappe.session.user);
            
            if (sidebar && frappeReady) {
                clearInterval(interval);
                console.log("[Global Customization] Sidebar & Frappe ready. Triggering render...");
                render_global_dashboard_sidebar();
            }
            
            if (attempts > 20) {
                clearInterval(interval);
                console.log("[Global Customization] Check timed out after 10 seconds.");
            }
        }, 500);
    }

    function render_global_dashboard_sidebar() {
        if (document.getElementById('da-sidebar-dashboards-section')) {
            console.log("[Global Customization] Section already rendered, skipping.");
            return;
        }

        const sidebar = document.querySelector('.desk-sidebar, .layout-side, .sidebar-left, .standard-sidebar');
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
                link.href = `/app/workspace/${encodeURIComponent(w.name)}`;
                
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    frappe.set_route('workspace', w.name);
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

            // Re-query sidebar in case it changed during the API call
            const currentSidebar = document.querySelector('.desk-sidebar, .layout-side, .sidebar-left, .standard-sidebar');
            if (!currentSidebar) {
                console.log("[Global Customization] Active sidebar disappeared during API call.");
                return;
            }

            const userProfile = currentSidebar.querySelector('.user-menu, [class*="user-profile"], [class*="avatar"]');
            if (userProfile && userProfile.parentNode === currentSidebar) {
                currentSidebar.insertBefore(section, userProfile);
            } else {
                currentSidebar.appendChild(section);
            }
            console.log("[Global Customization] Successfully rendered shortcuts section!");

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
