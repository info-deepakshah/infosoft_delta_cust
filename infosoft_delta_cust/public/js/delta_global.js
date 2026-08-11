/*
 * Global Navbar Workspace Shortcut Customization
 * Injected dynamically on Desk load/page change
 */
(function() {
    function render_global_dashboard_sidebar() {
        // Prevent duplicate rendering
        if (document.getElementById('da-sidebar-dashboards-section')) return;

        // Try to find the left sidebar container
        const sidebar = document.querySelector('.desk-sidebar, .layout-side, .sidebar-left, .standard-sidebar');
        if (!sidebar) return;

        const userEmail = frappe.session.user;

        // Query database for private workspaces
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
            callback: function(r) {
                const workspaces = r.message || [];
                
                // Filter workspaces: matches if name contains user's email, or if user is owner
                const userWorkspaces = workspaces.filter(w => {
                    return w.name.includes(userEmail) || w.owner === userEmail;
                });

                if (userWorkspaces.length === 0) return;

                // Create a container for our workspaces section
                const section = document.createElement('div');
                section.id = 'da-sidebar-dashboards-section';
                section.style.cssText = 'margin-top: 15px; border-top: 1px solid rgba(0,0,0,0.05); padding-top: 10px;';

                // Section Title Label
                const title = document.createElement('div');
                title.style.cssText = 'padding: 6px 16px; font-size: 10px; font-weight: bold; text-transform: uppercase; color: #888; letter-spacing: 0.8px;';
                title.innerText = 'My Workspaces';
                section.appendChild(title);

                // Add links for each workspace
                userWorkspaces.forEach(w => {
                    // Strip the user email suffix from name for a clean display label
                    let displayName = w.name.split('-' + userEmail)[0] || w.title || w.name;
                    displayName = displayName.trim();

                    const link = document.createElement('a');
                    link.className = 'da-sidebar-item';
                    link.style.cssText = 'display: flex; align-items: center; padding: 7px 16px; font-size: 12.5px; color: #444; text-decoration: none; transition: background 0.15s, color 0.15s; border-radius: 4px; margin: 2px 8px; cursor: pointer;';
                    link.href = `/app/workspace/${encodeURIComponent(w.name)}`;
                    
                    // SPA route transitions on click
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

                // Find where to insert: usually under the standard list, or at the bottom
                // We'll append it before the user profile element (usually at the very bottom, or just append to the sidebar wrapper)
                const userProfile = sidebar.querySelector('.user-menu, [class*="user-profile"], [class*="avatar"]');
                if (userProfile && userProfile.parentNode === sidebar) {
                    sidebar.insertBefore(section, userProfile);
                } else {
                    sidebar.appendChild(section);
                }

                // Inject hover style once
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
        });
    }

    // Bind listeners
    if (typeof frappe !== 'undefined') {
        $(document).ready(function() {
            render_global_dashboard_sidebar();
        });
        $(document).on('page-change', function() {
            render_global_dashboard_sidebar();
        });
    }
})();
