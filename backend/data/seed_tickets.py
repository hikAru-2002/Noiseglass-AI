"""Synthetic support ticket dataset generator."""
import json
import random
from datetime import datetime, timedelta


def generate_tickets(seed=None, count=85):
    """Generate realistic, messy support tickets for Flowline SaaS."""
    if seed is not None:
        random.seed(seed)
    
    categories = [
        "workflow_automation",
        "integration",
        "performance",
        "ui_ux",
        "billing",
        "data_export",
        "api",
        "documentation",
    ]
    
    templates = {
        "workflow_automation": [
            "Can't get my workflow to trigger on schedule",
            "Workflow keeps failing silently",
            "Why doesn't my automation run at midnight?",
            "Scheduled workflows not executing",
            "My workflow is broken",
            "Automation stopped working last week",
        ],
        "integration": [
            "Slack integration keeps disconnecting",
            "Can't connect to Salesforce",
            "Integration with Zapier broken",
            "Webhook not firing",
            "API integration failing",
            "Third-party sync issues",
        ],
        "performance": [
            "Dashboard is slow",
            "App freezes when I load large datasets",
            "Slow performance with 10k+ records",
            "Why is this so laggy?",
            "Performance degradation",
            "Takes forever to load",
        ],
        "ui_ux": [
            "UI is confusing",
            "Where is the export button?",
            "Can't find the settings",
            "Interface is unintuitive",
            "Button placement is weird",
            "Navigation is broken",
        ],
        "billing": [
            "Why was I charged twice?",
            "Billing issue on my account",
            "Unexpected charge",
            "Can't update payment method",
            "Invoice is wrong",
            "Subscription renewal failed",
        ],
        "data_export": [
            "Can't export my data",
            "Export feature not working",
            "CSV export is broken",
            "Data export failing",
            "How do I export to Excel?",
            "Export button does nothing",
        ],
        "api": [
            "API rate limiting too strict",
            "API documentation is outdated",
            "API endpoint returning 500",
            "Authentication failing",
            "API key not working",
            "REST API issues",
        ],
        "documentation": [
            "Documentation is unclear",
            "No docs for this feature",
            "Tutorial is outdated",
            "Can't find help",
            "Documentation missing",
            "Docs don't match the UI",
        ],
    }
    
    # Noise: off-topic, vague, or duplicate-ish tickets
    noise = [
        "Hello?",
        "Is anyone there?",
        "Help",
        "Not working",
        "Broken",
        "Fix this",
        "Urgent!!!",
        "ASAP",
        "Thanks",
        "Great product!",
        "Love it",
        "When is the next update?",
        "Can you add feature X?",
        "Competitor has this",
        "Why is this so expensive?",
    ]
    
    base_date = datetime.now() - timedelta(days=28)
    tickets = []
    
    for i in range(count):
        # 70% real issues, 30% noise
        if random.random() < 0.7:
            category = random.choice(categories)
            description = random.choice(templates[category])
        else:
            category = "other"
            description = random.choice(noise)
        
        ticket_date = base_date + timedelta(
            days=random.randint(0, 27),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        
        tickets.append({
            "id": f"TKT-{1000 + i}",
            "timestamp": ticket_date.isoformat(),
            "category": category,
            "description": description,
            "customer": f"customer_{random.randint(1, 50)}",
            "severity": random.choice(["low", "medium", "high"]),
        })
    
    return sorted(tickets, key=lambda x: x["timestamp"])


if __name__ == "__main__":
    tickets = generate_tickets(seed=42)
    with open("tickets.json", "w") as f:
        json.dump(tickets, f, indent=2)
    print(f"Generated {len(tickets)} tickets")

