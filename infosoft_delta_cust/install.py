from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup_custom_fields() -> None:
	"""
	Ensure `custom_internal_cc_emails` and `custom_sender_email` exist on Request for Quotation
	and Purchase Order without overwriting existing separate-tab (`POD3 Details` / `POD Details`) placement.
	"""
	custom_fields: dict[str, list[dict]] = {}

	target_configs = [
		("Request for Quotation", "custom_pod3_rfq_email_col", "transaction_date", 0),
		("Purchase Order", "custom_email_recipient", "contact_email", 1),
	]

	for doctype, preferred_after, fallback_after, is_hidden in target_configs:
		if not frappe.db.exists("DocType", doctype):
			continue

		anchor = (
			preferred_after
			if frappe.db.exists("Custom Field", f"{doctype}-{preferred_after}")
			else fallback_after
		)

		candidate_fields: list[dict] = [
			{
				"fieldname": "custom_internal_cc_emails",
				"label": "Internal CC Emails",
				"fieldtype": "Small Text",
				"insert_after": anchor,
				"default": "",
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

		missing_fields = [
			f
			for f in candidate_fields
			if not frappe.db.exists("Custom Field", f"{doctype}-{f['fieldname']}")
		]
		if missing_fields:
			custom_fields[doctype] = missing_fields

	if custom_fields:
		create_custom_fields(custom_fields, update=False)
