frappe.ui.form.on("Purchase Order", {
	refresh(frm) {
		frappe.call({
			method: "infosoft_delta_cust.utils.email_utils.get_outgoing_email_options",
			callback(r) {
				const data = (r && r.message) || {};
				const emails = data.emails || [];
				const default_sender = data.default_sender || "";

				if (frm.fields_dict.custom_sender_email) {
					frm.set_df_property("custom_sender_email", "options", emails);
					if (!frm.doc.custom_sender_email && default_sender && frm.is_new()) {
						frm.set_value("custom_sender_email", default_sender);
					}
				}

				if (frm.doc.docstatus === 1) {
					frm.add_custom_button(__("Send PO Email"), () => {
						const d = new frappe.ui.Dialog({
							title: __("Send Purchase Order Email"),
							fields: [
								{
									label: __("From Email"),
									fieldname: "sender_email",
									fieldtype: emails.length ? "Select" : "Data",
									options: emails,
									default: frm.doc.custom_sender_email || default_sender,
									reqd: emails.length ? 1 : 0,
								},
								{
									label: __("Internal CC Emails (comma-separated)"),
									fieldname: "cc_emails",
									fieldtype: "Small Text",
									default: frm.doc.custom_internal_cc_emails || "",
								},
							],
							primary_action_label: __("Send Email"),
							primary_action(values) {
								d.hide();
								frm.call({
									doc: frm.doc,
									method: "send_po_email_with_cc",
									freeze: true,
									freeze_message: __("Dispatching Purchase Order email..."),
									args: {
										sender_email: values.sender_email || "",
										cc_emails: values.cc_emails || "",
									},
									callback() {
										frm.reload_doc();
									},
								});
							},
						});
						d.show();
					});
				}
			},
		});
	},
});
