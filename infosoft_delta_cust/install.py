from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup_custom_fields() -> None:
	"""
	Ensure `custom_internal_cc_emails` and `custom_sender_email` exist on Request for Quotation
	(visible for RFQ DocType flow) and Purchase Order (hidden on PO Form — managed via POD3 flow).
	"""
	custom_fields: dict[str, list[dict]] = {}

	target_configs = [
		("Request for Quotation", "transaction_date", 0),
		("Purchase Order", "contact_email", 1),
	]

	for doctype, fallback_after, is_hidden in target_configs:
		if not frappe.db.exists("DocType", doctype):
			continue

		fields_to_ensure: list[dict] = [
			{
				"fieldname": "custom_internal_cc_emails",
				"label": "Internal CC Emails",
				"fieldtype": "Small Text",
				"insert_after": fallback_after,
				"allow_on_submit": 1,
				"hidden": is_hidden,
				"description": "Comma-separated internal email addresses to CC when sending to supplier.",
			},
			{
				"fieldname": "custom_sender_email",
				"label": "From Email",
				"fieldtype": "Autocomplete",
				"insert_after": "custom_internal_cc_emails",
				"allow_on_submit": 1,
				"no_copy": 0,
				"hidden": is_hidden,
				"description": "Outgoing email account used to send this document (defaults to logged-in user).",
			},
		]

		custom_fields[doctype] = fields_to_ensure

	if custom_fields:
		create_custom_fields(custom_fields, update=True)
