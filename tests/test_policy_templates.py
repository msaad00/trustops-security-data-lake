"""Policy template catalog validation and rendering."""

from __future__ import annotations

from security_lakehouse.policy_templates import (
    get_policy_template,
    list_policy_templates,
    render_policy_template,
    validate_policy_template_catalog,
)


def test_catalog_lists_core_templates() -> None:
    templates = list_policy_templates()
    ids = {row["template_id"] for row in templates}
    assert "information-security-policy" in ids
    assert "access-control-policy" in ids
    assert not validate_policy_template_catalog()


def test_render_substitutes_variables() -> None:
    template = get_policy_template("acceptable-use-policy")
    assert template is not None
    rendered = render_policy_template(
        template,
        {"company_name": "Acme Corp", "policy_owner": "CISO", "effective_date": "2026-01-01"},
    )
    assert "Acme Corp" in rendered
    assert "{{company_name}}" not in rendered
