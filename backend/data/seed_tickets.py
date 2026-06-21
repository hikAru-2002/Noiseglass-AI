"""
Synthetic support ticket dataset for "Flowline" — a fictional B2B workflow
automation SaaS product. Tickets are intentionally noisy: duplicates with
different phrasing, vague one-liners, off-topic tickets, and a mix of
severities, spread across a 4-week window so trend-over-time logic has
something real to chew on.
"""

from datetime import datetime, timedelta, timezone
import random

PRODUCT_NAME = "Flowline"

# Each tuple: (days_ago_min, days_ago_max, count, template_list)
# Templates intentionally vary in phrasing/specificity to simulate real users.

TEMPLATES = {
    "csv_export_confusion": [
        "Export to CSV is missing the status column, is this a bug?",
        "When I export my workflow report to CSV the dates show up in the wrong timezone",
        "csv export button greyed out on the reports page, not sure why",
        "Exported file only has 200 rows but I have way more records than that",
        "Can't figure out where the export option even is on the new reports UI",
        "CSV export from last week's run is missing half my custom fields",
        "Tried exporting twice today, file downloads but it's empty",
    ],
    "integration_auth_failure": [
        "Salesforce integration keeps saying 'token expired' even right after I reconnect it",
        "Getting an auth error every time I try to sync our HubSpot account",
        "Slack integration disconnected itself overnight, had to redo the whole oauth flow",
        "Why does my Salesforce connection break every few days? Very annoying",
        "Cannot authenticate Google Workspace connector, just spins forever",
        "integration error: 'invalid_grant' when reconnecting Salesforce",
        "HubSpot sync stopped working after their recent update on their end I think?",
    ],
    "onboarding_step_confusion": [
        "Stuck on step 3 of setup, the 'connect your first trigger' button does nothing",
        "Onboarding checklist says I need to add a trigger but I don't see where",
        "Is there a guide for setting up my first workflow? The wizard is confusing",
        "New team member couldn't get past account setup, kept getting stuck on permissions step",
        "the trigger setup screen during onboarding doesn't explain what 'event source' means",
        "Onboarding wizard crashed halfway through for our new hire",
        "Confused about which plan tier unlocks the advanced trigger options during setup",
    ],
    "workflow_builder_lag": [
        "Workflow builder is extremely slow today, taking 10+ seconds to drag a node",
        "Canvas lags badly once I have more than ~15 steps in a workflow",
        "Builder UI freezes when I try to add a conditional branch",
        "Is anyone else seeing major lag in the workflow editor this week?",
        "drag and drop in the builder is janky, nodes snap to wrong position",
    ],
    "billing_seat_confusion": [
        "We were charged for 12 seats but only have 8 active users, can you fix this",
        "How do I remove an inactive teammate from billing so we stop paying for their seat",
        "Invoice this month is higher than expected, did pricing change?",
        "Trying to downgrade our plan but the billing page just shows a spinner",
        "Got double charged this month, please refund",
    ],
    "notification_overload": [
        "Getting way too many Slack notifications from Flowline, can I batch them?",
        "Email alerts fire for every single workflow run even successful ones, very noisy",
        "How do I turn off notifications for just one specific workflow",
        "Notification settings page doesn't save my preferences, resets every time",
    ],
    "feature_request_misc": [
        "Would love a dark mode for the workflow builder",
        "Any plans to support conditional logic with OR statements, not just AND?",
        "Can you add a way to duplicate an entire workflow folder at once?",
        "Feature request: version history for workflows so we can roll back changes",
    ],
    "vague_or_offtopic": [
        "this isnt working",
        "hey can someone call me",
        "not sure whats going on but my stuff looks broken",
        "thanks for the help earlier!",
        "is there a phone number I can call instead of chat",
        "love the product, just wanted to say that",
        "question about your SOC2 report for our security team",
    ],
}

CUSTOMER_NAMES = [
    "Priya Natarajan", "Mark Chen", "Sofia Reyes", "Tom Whitfield", "Aisha Bello",
    "Derek Park", "Lena Brandt", "Carlos Mendes", "Grace Liu", "Jonas Berg",
    "Fatima Khan", "Ryan O'Sullivan", "Mei Tanaka", "Oliver Stone", "Nadia Popescu",
]

COMPANY_NAMES = [
    "Brightline Logistics", "Northwind Analytics", "Cedarbrook Health",
    "Vantage Retail Group", "Pinecrest Insurance", "Loop Manufacturing",
    "Harbor Point Media", "Quill & Co", "Atlas Freight", "Greenfield Robotics",
]


def generate_tickets(seed: int = 42):
    random.seed(seed)
    tickets = []
    ticket_id = 1001
    now = datetime.now(timezone.utc)

    # Weighting controls *trend* shape: which clusters are growing vs flat vs shrinking
    # across the 4-week window. (week 0 = most recent week, week 3 = oldest)
    cluster_week_weights = {
        "csv_export_confusion":     [6, 4, 2, 1],   # growing fast — good "rising" example
        "integration_auth_failure": [5, 5, 4, 5],   # steady, chronic issue
        "onboarding_step_confusion":[7, 3, 2, 1],   # growing — tie to recent release
        "workflow_builder_lag":     [4, 1, 0, 0],   # brand new this week — spike
        "billing_seat_confusion":   [2, 2, 3, 2],   # flat background noise
        "notification_overload":    [3, 3, 2, 3],   # flat
        "feature_request_misc":     [2, 2, 2, 2],   # flat, low volume
        "vague_or_offtopic":        [3, 2, 3, 2],   # noise floor
    }

    for cluster, weeks in cluster_week_weights.items():
        templates = TEMPLATES[cluster]
        for week_idx, count in enumerate(weeks):
            for _ in range(count):
                days_ago = week_idx * 7 + random.randint(0, 6)
                created = now - timedelta(days=days_ago, hours=random.randint(0, 23))
                text = random.choice(templates)
                tickets.append({
                    "id": f"TCK-{ticket_id}",
                    "created_at": created.isoformat(),
                    "customer_name": random.choice(CUSTOMER_NAMES),
                    "company": random.choice(COMPANY_NAMES),
                    "channel": random.choice(["email", "chat", "in-app"]),
                    "subject": text[:60],
                    "body": text,
                    "_true_cluster": cluster,  # ground truth, NOT shown to the model — used only for our own eval/demo narration
                })
                ticket_id += 1

    random.shuffle(tickets)
    return tickets


if __name__ == "__main__":
    import json
    data = generate_tickets()
    print(f"Generated {len(data)} tickets")
    with open("tickets.json", "w") as f:
        json.dump(data, f, indent=2)
