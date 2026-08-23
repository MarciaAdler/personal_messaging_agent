import json
import logging
import anthropic
from app.config import settings, local_today

log = logging.getLogger("clara.agent_brain")
_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are Clara, a helpful personal scheduling assistant reachable over text message (SMS).
You help the user manage their day using their Google Calendar (read-only) and their Notion to-do list.

You can NEVER edit or delete calendar events -- calendar is read-only for you.
You can NEVER delete to-do items -- you may only ADD new items or UPDATE their status to done.

You will be given:
- The user's current open to-do items (with a reference number and Notion page_id for each)
- The user's remaining calendar events for today (read-only, informational)
- The user's incoming message

Decide the user's intent and respond with ONLY a JSON object (no markdown fences, no preamble), with this shape:
{
  "intent": "complete_item" | "add_item" | "query_outstanding" | "chat",
  "page_ids_to_complete": [list of page_id strings, empty if not applicable],
  "new_item_title": "string or null",
  "new_item_due_date": "YYYY-MM-DD or null",
  "reply": "a short, warm, natural text reply confirming what you did or answering their question"
}

Rules:
- If the user references a to-do by its reference number (e.g. "mark 2 done", "finished #3"), map it to the correct page_id using the provided list.
- If the user describes a completed task in words (e.g. "I finished the client report"), match it against the open to-do titles as best you can. If genuinely ambiguous or no match, set intent to "chat" and ask a clarifying question in "reply".
- If the user asks to add something ("add: call the dentist tomorrow", "remind me to buy milk"), set intent "add_item", extract a clean title, and a due_date only if one is clearly implied (else null).
- If the user asks what's outstanding / what's left / what's on my plate, with no date mentioned, set intent "query_outstanding" and in "reply" list ONLY the open to-do items whose due date is today (today's date is given below). Do not mention items due on other dates, even though you can see them in the list.
- If the user asks about a specific day instead (e.g. "what do I have due tomorrow", "what's due Friday", "anything due 8/12"), set intent "query_outstanding" and in "reply" list ONLY the open to-do items whose due date matches that day. Work out the target date from today's date given below.
- If the user explicitly asks for everything / all outstanding items regardless of date, set intent "query_outstanding" and list all open to-do items provided, each with its due date.
- Keep replies concise and conversational, suitable for a text message. Use the person's actual item titles, not the reference numbers, when confirming completions.
"""


def _format_todos(open_todos):
    if open_todos is None:
        return "(couldn't load to-dos right now -- Notion may be unavailable)"
    if not open_todos:
        return "(none)"
    lines = []
    for t in open_todos:
        due = f" (due {t['due_date']})" if t.get("due_date") else ""
        lines.append(f"[{t['num']}] {t['title']}{due} -- page_id: {t['page_id']}")
    return "\n".join(lines)


def _format_events(events):
    if events is None:
        return "(couldn't load calendar right now -- Google Calendar may be unavailable)"
    if not events:
        return "(none)"
    lines = []
    for e in events:
        if e["all_day"]:
            lines.append(f"{e['summary']} (all day)")
        else:
            lines.append(f"{e['start']}-{e['end']}: {e['summary']}")
    return "\n".join(lines)


def interpret_message(user_text: str, open_todos: list, remaining_events: list) -> dict:
    """
    open_todos: list of dicts with num, page_id, title, due_date
    remaining_events: list of dicts from google_calendar module
    """
    user_prompt = f"""Today's date: {local_today().isoformat()}

Open to-do items:
{_format_todos(open_todos)}

Remaining calendar events today:
{_format_events(remaining_events)}

User's message: "{user_text}"

Respond with only the JSON object described in the system prompt."""

    try:
        resp = _client.messages.create(
            model=settings.CLARA_MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text").strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        log.error("interpret_message failed: %s", e)
        return {
            "intent": "chat",
            "page_ids_to_complete": [],
            "new_item_title": None,
            "new_item_due_date": None,
            "reply": "Sorry, I got a little confused there -- could you rephrase that?",
        }


def compose_daily_message(kind: str, events: list, todos: list) -> str:
    """
    kind: "morning" | "afternoon" | "evening"
    Uses Claude to write a warm, concise text summary. Falls back to a
    simple template if the API call fails for any reason.
    """
    try:
        prompts = {
            "morning": "Write a brief, warm good-morning text message summarizing today's calendar events and today's to-do items (all provided items are due today). Sign off as Clara.",
            "afternoon": "Write a brief 5pm text check-in listing the to-do items due today that are still outstanding (not completed; all provided items are due today). If none are outstanding, congratulate the user. Sign off as Clara.",
            "evening": "Write a brief 9pm text preview of tomorrow: tomorrow's calendar events and tomorrow's to-do items (all provided items are due tomorrow). If there's nothing on either, say so simply. Sign off as Clara.",
        }
        user_prompt = f"""{prompts[kind]}

Calendar events:
{_format_events(events)}

To-do items:
{_format_todos(todos)}
"""
        resp = _client.messages.create(
            model=settings.CLARA_MODEL,
            max_tokens=400,
            system="You are Clara, a warm and concise personal assistant writing a text message. "
            "If a section below says it couldn't load, briefly mention that it's temporarily "
            "unavailable rather than implying there's simply nothing there.",
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in resp.content if block.type == "text").strip()
    except Exception:
        return _fallback_message(kind, events, todos)


def _fallback_message(kind, events, todos):
    if kind == "morning":
        return f"Good morning! Here's today:\n\nCalendar:\n{_format_events(events)}\n\nTo-do:\n{_format_todos(todos)}"
    if kind == "afternoon":
        if todos is None:
            return "Heads up -- I couldn't load your to-do list from Notion just now, so I can't tell you what's still outstanding today."
        if not todos:
            return "Nice work -- nothing outstanding on your to-do list right now!"
        return f"Still outstanding today:\n{_format_todos(todos)}"
    if kind == "evening":
        return f"Here's a look at tomorrow:\n{_format_events(events)}"
    return "Hi, it's Clara!"
