import os
import json
import re
import time
from datetime import date
from dotenv import load_dotenv
import anthropic
import resend

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
RESEND_API_KEY = os.environ["RESEND_API_KEY"]
TO_EMAIL = os.environ["TO_EMAIL"]
FROM_EMAIL = os.environ["FROM_EMAIL"]

STORY_LOG_PATH = "story_log.json"

SYSTEM_PROMPT = """You are "The Algorithm," a sharp, dramatically entertaining AI news correspondent writing a morning briefing for a Gen AI product lead at American Express who focuses on the FRONTEND of Gen AI products — the customer-facing UX, design, and product experience. They work in fintech but also love hearing about AI in dining, travel, events, and consumer apps like Spotify.

Your briefing style: reality TV gossip meets Wall Street analyst. Think "Real Housewives meets Bloomberg." You narrate corporate AI developments like they're dramatic plot twists — with receipts. You're witty, a little catty, occasionally gleeful — but NEVER hyped or dishonest. No "this changes everything." No breathless clickbait. Be real. Be fair. Be entertaining.

For EACH story:
1. Write a sassy but accurate headline (no hyperbole)
2. Write 2-4 sentences of dramatic but factual narrative in your gossip-analyst voice
3. User problem being solved: 1-2 sentences, plain English
4. Amex angle: What does this mean for their Gen AI frontend role at Amex? Be specific — should they explore this model/framework/UX pattern? Is there a card benefit, travel, dining, or customer experience parallel?
5. Source: publication name and URL

Focus on: new AI model releases, fintech AI products, AI in dining/travel/events, consumer AI UX (especially clever design and frontend patterns), agentic AI architectures, AI design patterns worth stealing for customer-facing products.

Keep the FULL briefing to a 5-minute read (~800 words) unless there's genuinely a lot happening (up to ~1200 words). Cover 4-7 stories. Skip filler and incremental non-news. Only include things worth actually reading.

Start with a short 1-sentence "mood of the day" opener (dramatic, like a TV show cold open).

Format your response as JSON. Output raw JSON only — no markdown fences, no backticks, no explanation before or after:
{
  "mood": "one sentence dramatic opener",
  "stories": [
    {
      "headline": "sassy headline",
      "category": "one of: Model Drop, Fintech AI, AI UX, Travel & Dining, Agentic AI, Consumer AI",
      "narrative": "2-4 sentence gossip-analyst narrative",
      "problem": "user problem being solved",
      "amex": "specific amex/frontend angle",
      "source_name": "Publication Name",
      "source_url": "https://..."
    }
  ],
  "closing": "one cheeky closing line like a TV episode tag"
}"""

CATEGORY_COLORS = {
    "Model Drop": "#e91e63",
    "Fintech AI": "#43a047",
    "AI UX": "#1e88e5",
    "Travel & Dining": "#fb8c00",
    "Agentic AI": "#8e24aa",
    "Consumer AI": "#f4511e",
}


def load_recent_topics() -> list[dict]:
    if not os.path.exists(STORY_LOG_PATH):
        return []
    try:
        with open(STORY_LOG_PATH) as f:
            entries = json.load(f)
        return entries[-7:]
    except Exception:
        return []


def save_story_log(today: str, stories: list[dict]) -> None:
    entries = load_recent_topics()
    entries.append({"date": today, "headlines": [s["headline"] for s in stories]})
    entries = entries[-7:]
    with open(STORY_LOG_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def build_user_message(today: str, recent: list[dict]) -> str:
    msg = (
        f"Today is {today}. Search the web for the most notable AI news from the last "
        "24-48 hours and generate my morning briefing. Focus on stories that dropped since "
        "yesterday morning. If it's been a quiet news day, be honest and go deeper on 3-4 "
        "quality stories rather than padding with fluff."
    )
    if recent:
        covered = "\n".join(
            f"- {e['date']}: {', '.join(e['headlines'])}" for e in recent
        )
        msg += (
            f"\n\nThese topics were already covered this week — find different stories "
            f"and avoid repeating these:\n{covered}"
        )
    return msg


def fetch_briefing(today: str, recent: list[dict]) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    messages = [{"role": "user", "content": build_user_message(today, recent)}]

    for iteration in range(10):
        for attempt in range(5):
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=8000,
                    system=SYSTEM_PROMPT,
                    tools=[{
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": 5,
                    }],
                    messages=messages,
                )
                break
            except anthropic.RateLimitError:
                if attempt == 4:
                    raise
                wait = min(30 * (2 ** attempt), 120)
                print(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)

        print(f"Iteration {iteration}: stop_reason={response.stop_reason}")

        if response.stop_reason in ("end_turn", "max_tokens"):
            text_parts = [block.text for block in response.content if block.type == "text"]
            if not text_parts:
                raise RuntimeError(
                    f"stop_reason={response.stop_reason} but no text blocks. "
                    f"Block types: {[b.type for b in response.content]}"
                )
            raw = "\n".join(text_parts).strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```\s*$", "", raw)
            raw = raw.strip()
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end != -1:
                raw = raw[start:end + 1]
            return json.loads(raw)

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = [
                {"type": "tool_result", "tool_use_id": block.id, "content": ""}
                for block in response.content
                if block.type == "tool_use"
            ]
            messages.append({"role": "user", "content": tool_results})
            continue

        raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")

    raise RuntimeError("Web search loop exceeded max iterations")


def build_html(data: dict, today: str) -> str:
    def story_card(story: dict) -> str:
        category = story.get("category", "AI UX")
        color = CATEGORY_COLORS.get(category, "#1e88e5")
        return f"""
        <div style="background:#ffffff;border-radius:12px;margin-bottom:24px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.07);">
          <div style="height:4px;background:{color};"></div>
          <div style="padding:24px 28px;">
            <span style="display:inline-block;background:{color};color:#fff;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;border-radius:20px;padding:4px 12px;margin-bottom:14px;">{story["category"]}</span>
            <h2 style="margin:0 0 12px;font-size:19px;font-weight:700;color:#1a1a2e;line-height:1.35;">{story["headline"]}</h2>
            <p style="margin:0 0 18px;font-size:15px;line-height:1.65;color:#444;">{story["narrative"]}</p>
            <div style="background:linear-gradient(135deg,#fff0f6,#f0f4ff);border-radius:8px;padding:16px 20px;margin-bottom:16px;">
              <p style="margin:0 0 10px;font-size:13px;"><span style="font-weight:700;color:#880e4f;">Problem Solved&nbsp;&nbsp;</span><span style="color:#555;">{story["problem"]}</span></p>
              <p style="margin:0;font-size:13px;"><span style="font-weight:700;color:#283593;">Amex Angle&nbsp;&nbsp;</span><span style="color:#555;">{story["amex"]}</span></p>
            </div>
            <a href="{story["source_url"]}" style="font-size:12px;color:#8e24aa;text-decoration:none;font-weight:600;">&#8599;&nbsp;{story["source_name"]}</a>
          </div>
        </div>"""

    stories_html = "\n".join(story_card(s) for s in data.get("stories", []))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@1,600;1,700&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<title>The Algorithm — {today}</title>
</head>
<body style="margin:0;padding:0;background:linear-gradient(135deg,#fff0f6 0%,#f0f4ff 100%);font-family:'DM Sans',Arial,sans-serif;">
  <div style="max-width:680px;margin:0 auto;padding:32px 16px 48px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#880e4f 0%,#283593 100%);border-radius:16px;padding:36px 32px 28px;margin-bottom:24px;text-align:center;">
      <div style="font-family:'Cormorant Garamond',Georgia,serif;font-style:italic;font-size:46px;font-weight:700;color:#ffffff;line-height:1;letter-spacing:-0.5px;">The Algorithm</div>
      <div style="color:rgba(255,255,255,0.7);font-size:13px;margin-top:8px;letter-spacing:0.1em;text-transform:uppercase;">Your Morning AI Briefing &middot; {today}</div>
    </div>

    <!-- Mood opener -->
    <div style="background:linear-gradient(135deg,#fce4ec,#ede7f6);border-radius:12px;padding:20px 24px;margin-bottom:28px;border-left:4px solid #e91e63;">
      <p style="margin:0;font-size:16px;font-style:italic;color:#4a1942;line-height:1.6;">{data.get("mood", "")}</p>
    </div>

    <!-- Stories -->
    {stories_html}

    <!-- Closing -->
    <div style="background:linear-gradient(135deg,#880e4f,#283593);border-radius:12px;padding:20px 24px;margin-top:8px;text-align:center;">
      <p style="margin:0;font-size:14px;font-style:italic;color:rgba(255,255,255,0.9);line-height:1.6;">{data.get("closing", "")}</p>
    </div>

    <!-- Footer -->
    <p style="text-align:center;font-size:11px;color:#999;margin-top:24px;">Generated by The Algorithm &middot; Powered by Claude &amp; Resend</p>
  </div>
</body>
</html>"""


def send_email(html: str, today: str) -> None:
    resend.api_key = RESEND_API_KEY
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": [TO_EMAIL],
        "subject": f"The Algorithm ☀️ {today}",
        "html": html,
    })


def main() -> None:
    today = date.today().strftime("%B %d, %Y")
    recent = load_recent_topics()
    print(f"Fetching briefing for {today} (avoiding {sum(len(e['headlines']) for e in recent)} recent stories)...")
    data = fetch_briefing(today, recent)
    stories = data.get("stories", [])
    print(f"Got {len(stories)} stories. Building email...")
    html = build_html(data, today)
    print("Sending email...")
    send_email(html, today)
    save_story_log(today, stories)
    print("Done! Briefing sent and story log updated.")


if __name__ == "__main__":
    main()
