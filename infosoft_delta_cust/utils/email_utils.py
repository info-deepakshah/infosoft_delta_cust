from __future__ import annotations

import frappe
from frappe import _


def parse_cc_emails(cc_raw: str | None, exclude_recipient: str | None = None) -> list[str]:
	"""Parse comma/semicolon/newline-separated CC emails, deduplicating case-insensitively."""
	raw = (cc_raw or "").strip()
	if not raw:
		return []

	normalized = raw.replace(";", ",").replace("\n", ",").replace("\r", ",")
	exclude_lower = (exclude_recipient or "").strip().lower()
	seen: set[str] = set()
	result: list[str] = []

	for part in normalized.split(","):
		email = part.strip()
		if not email or "@" not in email:
			continue
		email_lower = email.lower()
		if exclude_lower and email_lower == exclude_lower:
			continue
		if email_lower not in seen:
			seen.add(email_lower)
			result.append(email)

	return result


def get_logged_in_user_email() -> str:
	"""Resolve the current logged-in user's email address (empty string for Guest/non-email system users)."""
	user = (frappe.session.user or "").strip()
	if not user or user in ("Guest", "Administrator"):
		if user == "Administrator":
			admin_email = (frappe.db.get_value("User", "Administrator", "email") or "").strip()
			return admin_email if "@" in admin_email else ""
		return ""
	if "@" in user:
		return user
	db_email = (frappe.db.get_value("User", user, "email") or "").strip()
	return db_email if "@" in db_email else ""


def _fetch_outgoing_accounts() -> list[dict]:
	"""Return enabled outgoing Email Accounts ordered with logged-in user first, then purchase@*, then default."""
	if not frappe.db.exists("DocType", "Email Account"):
		return []

	user_email_low = get_logged_in_user_email().lower()
	accounts = frappe.get_all(
		"Email Account",
		filters={"enable_outgoing": 1},
		fields=["name", "email_id", "default_outgoing"],
		order_by="default_outgoing desc, name asc",
	)
	valid = [acc for acc in accounts if (acc.get("email_id") or "").strip()]
	valid.sort(
		key=lambda acc: (
			0 if (user_email_low and acc["email_id"].strip().lower() == user_email_low) else 1,
			0 if acc["email_id"].strip().lower().startswith("purchase@") else 1,
			0 if acc.get("default_outgoing") else 1,
			acc["email_id"].strip().lower(),
		)
	)
	return valid


def get_default_purchase_sender() -> str:
	"""Fallback outgoing Email Account starting with 'purchase@', else Default Outgoing."""
	accounts = _fetch_outgoing_accounts()
	if not accounts:
		return ""

	for acc in accounts:
		email_id = acc["email_id"].strip()
		if email_id.lower().startswith("purchase@"):
			return email_id

	for acc in accounts:
		if acc.get("default_outgoing"):
			return acc["email_id"].strip()

	return accounts[0]["email_id"].strip()


def get_default_sender_for_user() -> str:
	"""
	Option 1 Default Sender Priority:
	1. Logged-in user's email if configured as an enabled Outgoing Email Account
	2. Outgoing Email Account starting with 'purchase@'
	3. Default Outgoing Email Account
	"""
	accounts = _fetch_outgoing_accounts()
	if not accounts:
		return ""

	user_email_low = get_logged_in_user_email().lower()
	if user_email_low:
		for acc in accounts:
			email_id = acc["email_id"].strip()
			if email_id.lower() == user_email_low:
				return email_id

	return get_default_purchase_sender()


def resolve_sender_email(explicit_sender: str | None = None, doc=None) -> str | None:
	"""
	Resolve outgoing sender email address in priority order:
	1. Explicit `sender_email` argument (from POD3 or Desk dialog)
	2. `doc.custom_sender_email` field on RFQ / PO
	3. Logged-in user's enabled Outgoing Email Account
	4. Outgoing Email Account starting with `purchase@` / Default Outgoing
	"""
	candidate = (
		(explicit_sender or "").strip()
		or (getattr(doc, "custom_sender_email", None) or "").strip()
	)

	accounts = _fetch_outgoing_accounts()
	by_email = {acc["email_id"].strip().lower(): acc["email_id"].strip() for acc in accounts}
	by_name = {acc["name"].strip().lower(): acc["email_id"].strip() for acc in accounts}

	if candidate:
		cand_lower = candidate.lower()
		if cand_lower in by_email:
			return by_email[cand_lower]
		if cand_lower in by_name:
			return by_name[cand_lower]
		if accounts:
			frappe.throw(
				_(
					"Selected From Email '{0}' is not configured as an enabled Outgoing Email Account."
				).format(candidate)
			)
		return candidate

	default_sender = get_default_sender_for_user()
	return default_sender or None


@frappe.whitelist()
def get_outgoing_email_options() -> dict:
	"""Return outgoing email list, logged-in user default sender, and logged-in user default CC."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	accounts = _fetch_outgoing_accounts()
	seen: set[str] = set()
	emails: list[str] = []
	for acc in accounts:
		email_id = acc["email_id"].strip()
		if email_id.lower() not in seen:
			seen.add(email_id.lower())
			emails.append(email_id)

	user_email = get_logged_in_user_email()
	return {
		"emails": emails,
		"default_sender": get_default_sender_for_user(),
		"logged_in_email": user_email,
		"default_cc": user_email,
	}
