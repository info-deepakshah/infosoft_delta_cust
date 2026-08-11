/*
 * Global Navbar Dashboard Shortcut Icon Customization
 * Injected dynamically on Desk load/page change
 */
(function() {
    function render_global_dashboard_icon() {
        // Prevent duplicate rendering
        if (document.getElementById('da-global-dashboard-item')) return;

        let container = null;
        let insertBeforeNode = null;

        // 1. Try to find the notification/bell icon in the new v16 sidebar
        const v16Bell = document.querySelector('.desktop-notification-icon, .navbar-notification, .notifications-icon, [data-route="List/Notification Log"]');
        if (v16Bell) {
            container = v16Bell.parentNode;
            insertBeforeNode = v16Bell;
        }

        // 2. Try to find the legacy top navbar
        if (!container) {
            const legacyNav = document.querySelector('.navbar .navbar-collapse, .navbar .navbar-right, .navbar-right');
            if (legacyNav) {
                container = legacyNav;
                insertBeforeNode = legacyNav.firstChild;
            }
        }

        // 3. Try to find the main sidebar container
        if (!container) {
            const mainSidebar = document.querySelector('.desk-sidebar, .layout-side, .sidebar-left, .standard-sidebar, .sidebar-items');
            if (mainSidebar) {
                container = mainSidebar;
                insertBeforeNode = mainSidebar.firstChild;
            }
        }

        if (!container) {
            console.log("[Global Dashboard] Could not find navbar or sidebar container in the DOM.");
            return;
        }

        const itemContainer = document.createElement('div');
        itemContainer.id = 'da-global-dashboard-item';
        itemContainer.className = 'da-dashboard-nav-item';
        itemContainer.style.cssText = 'position: relative; cursor: pointer; padding: 12px 10px; font-size: 16px; display: flex; align-items: center; justify-content: center;';
        
        // 📊 Icon Trigger Markup
        itemContainer.innerHTML = `
            <span id="da-global-dashboard-trigger" title="My Dashboards" style="display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; font-size: 16px; padding: 2px;">📊</span>
        `;

        // Insert at the resolved position (next to bell or top of sidebar)
        container.insertBefore(itemContainer, insertBeforeNode);

        // Click handler to load/show dashboards list
        itemContainer.addEventListener('click', function(e) {
            e.stopPropagation();
            fetch_and_handle_dashboards();
        });

        // Click outside dropdown to dismiss it
        window.addEventListener('click', function(e) {
            const drop = document.getElementById('da-global-dashboard-drop');
            if (drop) {
                drop.style.display = 'none';
            }
        });
    }

    let cached_dashboards = null;

    function fetch_and_handle_dashboards() {
        // Toggle or create dropdown in body to prevent sidebar overflow clipping
        let drop = document.getElementById('da-global-dashboard-drop');
        if (!drop) {
            drop = document.createElement('div');
            drop.id = 'da-global-dashboard-drop';
            drop.className = 'da-dashboard-dropdown';
            drop.style.cssText = 'display: none; position: fixed; width: 260px; background: #ffffff; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); z-index: 100002; overflow: hidden; font-family: Arial, sans-serif; flex-direction: column;';
            drop.innerHTML = `
                <div class="da-dashboard-header" style="padding: 10px 15px; background: #fafafa; border-bottom: 1px solid rgba(0,0,0,0.06); font-weight: bold; font-size: 12px; color: #555; display: flex; justify-content: space-between; align-items: center;">
                    <span>My Dashboards</span>
                </div>
                <div id="da-global-dashboard-list" style="max-height: 250px; overflow-y: auto;">
                    <div style="padding: 15px; text-align: center; color: #888; font-size: 12px;">Loading dashboards...</div>
                </div>
            `;
            document.body.appendChild(drop);
        }

        // Use memory cache for instantaneous response
        if (cached_dashboards !== null) {
            handle_dashboard_selection(cached_dashboards);
            return;
        }

        // Query database for custom (private) dashboards owned by logged-in user
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Dashboard",
                filters: {
                    "is_standard": 0,
                    "owner": frappe.session.user
                },
                fields: ["name"],
                limit_page_length: 50
            },
            callback: function(r) {
                const list = r.message || [];
                cached_dashboards = list;
                handle_dashboard_selection(list);
            }
        });
    }

    function handle_dashboard_selection(dashboards) {
        const drop = document.getElementById('da-global-dashboard-drop');
        const listContainer = document.getElementById('da-global-dashboard-list');
        const trigger = document.getElementById('da-global-dashboard-item');
        if (!drop || !listContainer || !trigger) return;

        // Case 1: No private dashboards
        if (dashboards.length === 0) {
            frappe.show_alert({message: "No private dashboards configured for your account.", indicator: "orange"});
            drop.style.display = 'none';
            return;
        }

        // Case 2: Exactly 1 private dashboard -> Redirect immediately
        if (dashboards.length === 1) {
            frappe.set_route("dashboard-view", dashboards[0].name);
            return;
        }

        // Position dropdown relative to the trigger icon's viewport coordinates
        const rect = trigger.getBoundingClientRect();
        drop.style.top = rect.bottom + 'px';
        drop.style.left = rect.left + 'px';

        // Case 3: More than 1 private dashboard -> Toggle dropdown list
        if (drop.style.display === 'flex') {
            drop.style.display = 'none';
            return;
        }

        let html = '';
        dashboards.forEach(d => {
            html += `
                <div class="da-dashboard-item" style="padding: 10px 15px; border-bottom: 1px solid rgba(0,0,0,0.04); font-size: 12.5px; cursor: pointer; color: #333; transition: background 0.2s;" onclick="frappe.set_route('dashboard-view', '${d.name}')">
                    📊 <span style="font-weight: 500;">${d.name}</span>
                </div>
            `;
        });
        listContainer.innerHTML = html;
        drop.style.display = 'flex';

        // Inject dynamic hover styles once
        if (!document.getElementById('da-dashboard-item-style')) {
            const style = document.createElement('style');
            style.id = 'da-dashboard-item-style';
            style.innerHTML = `
                .da-dashboard-item:hover {
                    background-color: #f1f5f9 !important;
                    color: var(--primary) !important;
                }
            `;
            document.head.appendChild(style);
        }
    }

    // Bind listeners
    if (typeof frappe !== 'undefined') {
        $(document).ready(function() {
            render_global_dashboard_icon();
        });
        $(document).on('page-change', function() {
            render_global_dashboard_icon();
        });
    }
})();
