from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup_custom_fields() -> None:
	"""
	Ensure `custom_internal_cc_emails` (if not already present) and `custom_sender_email`
	exist on Request for Quotation and Purchase Order.
	"""
	custom_fields: dict[str, list[dict]] = {}

	target_configs = [
		("Request for Quotation", "transaction_date"),
		("Purchase Order", "contact_email"),
	]

	for doctype, fallback_after in target_configs:
		if not frappe.db.exists("DocType", doctype):
			continue

		fields_to_ensure: list[dict] = []
		has_cc_field = bool(
			frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": "custom_internal_cc_emails"})
		)

		if not has_cc_field:
			fields_to_ensure.append(
				{
					"fieldname": "custom_internal_cc_emails",
					"label": "Internal CC Emails",
					"fieldtype": "Small Text",
					"insert_after": fallback_after,
					"allow_on_submit": 1,
					"description": "Comma-separated internal email addresses to CC when sending to supplier.",
				}
			)

		fields_to_ensure.append(
			{
				"fieldname": "custom_sender_email",
				"label": "From Email",
				"fieldtype": "Autocomplete",
				"insert_after": "custom_internal_cc_emails",
				"allow_on_submit": 1,
				"no_copy": 0,
				"description": "Outgoing email account used to send this document (defaults to purchase email).",
			}
		)

		custom_fields[doctype] = fields_to_ensure

	if custom_fields:
		create_custom_fields(custom_fields, update=True)
