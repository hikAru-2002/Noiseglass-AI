"""Core pipeline: classify → cluster → summarize."""
import json
from collections import defaultdict
from datetime import datetime, timedelta
from anthropic import Anthropic

client = Anthropic()


def classify_tickets(tickets: list[dict]) -> list[dict]:
    """Pass 1: Use Claude to classify tickets into categories."""
    classified = []
    
    # Batch tickets for efficiency
    batch_size = 10
    for i in range(0, len(tickets), batch_size):
        batch = tickets[i : i + batch_size]
        
        prompt = "Classify each support ticket into ONE category and provide a normalized one-sentence issue description.\n\n"
        for ticket in batch:
            prompt += f"Ticket {ticket['id']}: {ticket['description']}\n"
        
        prompt += "\nRespond with JSON array: [{\"id\": \"TKT-XXX\", \"category\": \"...\", \"normalized\": \"...\"}]"
        
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            
            result_text = response.content[0].text
            # Extract JSON from response
            start = result_text.find("[")
            end = result_text.rfind("]") + 1
            if start >= 0 and end > start:
                results = json.loads(result_text[start:end])
                for result in results:
                    # Find original ticket and merge
                    for ticket in batch:
                        if ticket["id"] == result.get("id"):
                            ticket["category"] = result.get("category", ticket.get("category", "other"))
                            ticket["normalized"] = result.get("normalized", ticket["description"])
                            classified.append(ticket)
                            break
        except Exception as e:
            print(f"Classification error: {e}")
            # Fallback: keep original
            for ticket in batch:
                ticket["normalized"] = ticket["description"]
                classified.append(ticket)
    
    return classified


def cluster_tickets(tickets: list[dict]) -> dict:
    """Pass 2: Group by category and compute week-over-week trends."""
    clusters = defaultdict(list)
    
    for ticket in tickets:
        category = ticket.get("category", "other")
        clusters[category].append(ticket)
    
    # Compute trends
    trends = {}
    base_date = datetime.fromisoformat(tickets[0]["timestamp"]) if tickets else datetime.now()
    
    for category, group in clusters.items():
        weeks = defaultdict(int)
        for ticket in group:
            ticket_date = datetime.fromisoformat(ticket["timestamp"])
            week_offset = (ticket_date - base_date).days // 7
            weeks[week_offset] += 1
        
        week_list = sorted(weeks.items())
        trend = "stable"
        if len(week_list) >= 2:
            recent = week_list[-1][1]
            previous = week_list[-2][1]
            if recent > previous * 1.5:
                trend = "increasing"
            elif recent < previous * 0.67:
                trend = "decreasing"
        
        trends[category] = {
            "count": len(group),
            "trend": trend,
            "weekly_counts": dict(week_list),
            "samples": group[:3],  # First 3 tickets as samples
        }
    
    return trends


def summarize_signals(trends: dict) -> list[dict]:
    """Pass 3: Use Claude to write summaries for high-volume clusters."""
    signals = []
    
    # Filter to clusters with enough volume
    significant = {k: v for k, v in trends.items() if v["count"] >= 3}
    
    if not significant:
        return signals
    
    prompt = "Given these support ticket clusters, write a brief signal summary for each.\n\n"
    for category, data in significant.items():
        prompt += f"\n{category.upper()} ({data['count']} tickets, trend: {data['trend']})\n"
        for sample in data["samples"]:
            prompt += f"  - {sample.get('normalized', sample['description'])}\n"
    
    prompt += "\nRespond with JSON array: [{\"category\": \"...\", \"headline\": \"...\", \"action\": \"...\", \"severity\": \"low|medium|high\"}]"
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        
        result_text = response.content[0].text
        start = result_text.find("[")
        end = result_text.rfind("]") + 1
        if start >= 0 and end > start:
            summaries = json.loads(result_text[start:end])
            for summary in summaries:
                category = summary.get("category", "").lower().replace(" ", "_")
                if category in significant:
                    signals.append({
                        "category": category,
                        "headline": summary.get("headline", ""),
                        "action": summary.get("action", ""),
                        "severity": summary.get("severity", "medium"),
                        "count": significant[category]["count"],
                        "trend": significant[category]["trend"],
                        "samples": significant[category]["samples"],
                    })
    except Exception as e:
        print(f"Summarization error: {e}")
    
    # Sort by count descending
    signals.sort(key=lambda x: x["count"], reverse=True)
    return signals


def run_pipeline(tickets: list[dict]) -> dict:
    """Run the full pipeline: classify → cluster → summarize."""
    print(f"Starting pipeline with {len(tickets)} tickets...")
    
    print("Pass 1: Classifying...")
    classified = classify_tickets(tickets)
    
    print("Pass 2: Clustering and computing trends...")
    trends = cluster_tickets(classified)
    
    print("Pass 3: Summarizing signals...")
    signals = summarize_signals(trends)
    
    return {
        "tickets": classified,
        "trends": trends,
        "signals": signals,
    }

