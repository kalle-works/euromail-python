"""
EuroMail Python SDK — comprehensive example exercising every method.

Usage:
    EUROMAIL_API_KEY=em_live_... python examples/all_methods.py
"""
import os
import time
from euromail import EuroMail

client = EuroMail(api_key=os.environ["EUROMAIL_API_KEY"])


def main() -> None:
    # ---- Account ----
    account = client.get_account()
    print(f"Account: {account.name} ({account.plan})")

    # ---- API Keys ----
    api_key = client.create_api_key(name="test-key", scopes=["emails:send"])
    print(f"Created API key: {api_key.key_prefix}... (id: {api_key.id})")

    keys = client.list_api_keys()
    print(f"API keys: {len(keys)}")

    client.delete_api_key(api_key.id)
    print("Deleted API key")

    # ---- Domains ----
    test_domain = "test-sdk-example.com"
    domain = client.add_domain(test_domain)
    print(f"Added domain: {domain.domain} (id: {domain.id})")

    domain_detail = client.get_domain(domain.id)
    print(f"Domain DKIM selector: {domain_detail.dkim_selector}")

    verification = client.verify_domain(domain.id)
    spf = verification.checks.get("spf")
    print(f"Domain SPF verified: {spf.verified if spf else 'N/A'}")

    domains = client.list_domains(page=1, per_page=10)
    print(f"Domains: {len(domains.data)} total")

    # Tracking domain
    try:
        tracking = client.set_tracking_domain(domain.id, "track.test-sdk-example.com")
        print(f"Tracking domain set: {tracking}")

        track_verify = client.verify_tracking_domain(domain.id)
        print(f"Tracking verified: {track_verify}")

        client.remove_tracking_domain(domain.id)
        print("Removed tracking domain")
    except Exception as e:
        print(f"Tracking domain: {e}")

    client.delete_domain(domain.id)
    print("Deleted domain")

    # ---- Templates ----
    template_alias = f"test-welcome-{int(time.time())}"
    template = client.create_template(
        alias=template_alias,
        name="Test Welcome",
        subject="Welcome {{ name }}!",
        html_body="<p>Hello {{ name }}</p>",
    )
    print(f"Created template: {template.alias} (id: {template.id})")

    tmpl = client.get_template(template.id)
    print(f"Template subject: {tmpl.subject}")

    updated = client.update_template(
        template.id, name="Updated Welcome", subject=template.subject,
        html_body="<p>Updated {{ name }}</p>",
    )
    print(f"Updated template name: {updated.name}")

    templates = client.list_templates(page=1, per_page=10)
    print(f"Templates: {len(templates.data)}")

    client.delete_template(template.id)
    print("Deleted template")

    # ---- Emails ----
    from_domain = account.email.split("@")[1]
    sent = client.send_email(
        from_address=f"test@{from_domain}",
        to=account.email,
        subject="SDK test",
        text_body="Hello from the Python SDK example!",
    )
    print(f"Sent email: {sent.id} (status: {sent.status})")

    email = client.get_email(sent.id)
    print(f"Email to: {email.to_address}")

    emails = client.list_emails(page=1, per_page=5)
    print(f"Emails: {len(emails.data)}")

    # ---- Email Validation ----
    validation = client.validate_email("test@example.com")
    print(f"Validation: valid={validation.valid}, deliverable={validation.deliverable}")

    # ---- Webhooks ----
    webhook = client.create_webhook(
        url="https://httpbin.org/post",
        events=["delivered", "bounced"],
    )
    print(f"Created webhook: {webhook.id}")

    wh = client.get_webhook(webhook.id)
    print(f"Webhook events: {', '.join(wh.events)}")

    updated_wh = client.update_webhook(
        webhook.id,
        url="https://httpbin.org/post",
        events=["delivered", "bounced", "opened"],
        is_active=True,
    )
    print(f"Updated webhook events: {', '.join(updated_wh.events)}")

    webhooks = client.list_webhooks(page=1, per_page=10)
    print(f"Webhooks: {len(webhooks.data)}")

    try:
        test = client.test_webhook(webhook.id)
        print(f"Webhook test: {test.message}")
    except Exception as e:
        print(f"Webhook test: {e}")

    client.delete_webhook(webhook.id)
    print("Deleted webhook")

    # ---- Suppressions ----
    suppression = client.add_suppression("blocked@example.com", "manual")
    print(f"Added suppression: {suppression.email_address}")

    suppressions = client.list_suppressions(page=1, per_page=10)
    print(f"Suppressions: {len(suppressions.data)}")

    client.delete_suppression("blocked@example.com")
    print("Deleted suppression")

    # ---- Contact Lists ----
    contact_list = client.create_contact_list(name="SDK Test List")
    print(f"Created list: {contact_list.name} (id: {contact_list.id})")

    contact = client.add_contact(contact_list.id, email="user@example.com")
    print(f"Added contact: {contact.email}")

    bulk = client.bulk_add_contacts(
        contact_list.id,
        contacts=[{"email": "a@example.com"}, {"email": "b@example.com"}],
    )
    print(f"Bulk added: {bulk.inserted}/{bulk.total_requested}")

    contacts = client.list_contacts(contact_list.id, page=1, per_page=10)
    print(f"Contacts: {len(contacts.data)}")

    client.remove_contact(contact_list.id, "user@example.com")
    print("Removed contact")

    updated_list = client.update_contact_list(
        contact_list.id, name="Updated List", double_opt_in=False
    )
    print(f"Updated list: {updated_list.name}")

    lists = client.list_contact_lists()
    print(f"Contact lists: {len(lists)}")

    list_detail = client.get_contact_list(contact_list.id)
    print(f"List contacts: {list_detail.contact_count}")

    client.delete_contact_list(contact_list.id)
    print("Deleted contact list")

    # ---- Newsletters ----
    try:
        nl = client.create_newsletter(
            list_id="00000000-0000-0000-0000-000000000000",
            subject="Test Newsletter",
            from_address=account.email,
            html_body="<p>Newsletter content</p>",
        )
        print(f"Created newsletter: {nl.subject} (id: {nl.id})")

        nl_detail = client.get_newsletter(nl.id)
        print(f"Newsletter status: {nl_detail.status}")

        updated_nl = client.update_newsletter(nl.id, subject="Updated Newsletter")
        print(f"Updated newsletter: {updated_nl.subject}")

        newsletters = client.list_newsletters(limit=10)
        print(f"Newsletters: {len(newsletters)}")

        client.delete_newsletter(nl.id)
        print("Deleted newsletter")
    except Exception as e:
        print(f"Newsletter: {e}")

    # ---- Analytics ----
    overview = client.get_analytics_overview(period="30d")
    print(f"Analytics: {overview.total_sent} sent, {overview.total_delivered} delivered")

    timeseries = client.get_analytics_timeseries(period="7d")
    print(f"Timeseries points: {len(timeseries)}")

    domain_stats = client.get_analytics_domains(period="30d", limit=5)
    print(f"Domain analytics: {len(domain_stats)} domains")

    csv = client.export_analytics_csv(period="7d")
    print(f"CSV export: {len(csv)} bytes")

    # ---- Operations ----
    ops = client.list_operations(page=1, per_page=5)
    print(f"Operations: {len(ops.data)}")

    # ---- Audit Logs ----
    logs = client.list_audit_logs(page=1, per_page=5)
    print(f"Audit logs: {len(logs.data)}")

    # ---- Dead Letters ----
    dead_letters = client.list_dead_letters(count=5)
    print(f"Dead letters: {len(dead_letters)}")

    # ---- Inbound ----
    inbound = client.list_inbound_emails(page=1, per_page=5)
    print(f"Inbound emails: {len(inbound.data)}")

    routes = client.list_inbound_routes(page=1, per_page=5)
    print(f"Inbound routes: {len(routes.data)}")

    # ---- Billing ----
    plans = client.list_plans()
    print(f"Plans: {', '.join(p.plan for p in plans)}")

    sub = client.get_subscription()
    print(f"Subscription: {sub.plan} ({sub.subscription_status})")

    # ---- GDPR ----
    try:
        gdpr = client.gdpr_export("test@example.com")
        print(f"GDPR export: {gdpr['data']['email_address']}")
    except Exception as e:
        print(f"GDPR export: {e}")

    print("\nAll methods exercised successfully!")


if __name__ == "__main__":
    main()
