import logging
import datetime
from fastapi import FastAPI, Request, Response
from app.config import settings
from app import db, google_calendar, notion_todo, agent_brain, sms, scheduler as sched_module

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("clara")

app = FastAPI(title="Clara Agent")

_scheduler = None


@app.on_event("startup")
def on_startup():
    global _scheduler
    db.init_db()
    _scheduler = sched_module.start_scheduler()
    log.info("Clara is up.")


@app.get("/")
def health():
    return {"status": "Clara is running"}


@app.get("/privacy")
def privacy_policy():
    return Response(content=PRIVACY_POLICY_HTML, media_type="text/html")


@app.get("/terms")
def terms_of_service():
    return Response(content=TERMS_HTML, media_type="text/html")


@app.get("/consent")
def consent_form():
    return Response(content=_consent_form_html(), media_type="text/html")


@app.post("/consent")
async def consent_submit(request: Request):
    form = await request.form()
    phone = (form.get("phone") or "").strip()
    agreed = form.get("consent") == "on"

    if not phone:
        return Response(
            content=_consent_form_html(error="Please enter a phone number."),
            media_type="text/html",
            status_code=400,
        )

    if not agreed:
        return Response(content=CONSENT_DECLINED_HTML, media_type="text/html")

    db.save_consent(phone)

    if phone == settings.MY_PHONE_NUMBER:
        try:
            sms.send_message(
                "Welcome to Clara! You'll get daily schedule reminders by text. "
                "Reply STOP to unsubscribe, HELP for help. Msg&data rates may apply."
            )
        except Exception as e:
            log.error("Failed to send opt-in confirmation SMS: %s", e)

    return Response(content=CONSENT_THANKYOU_HTML, media_type="text/html")


def _consent_form_html(error: str = "") -> str:
    error_html = f'<p style="color:#b00020;">{_xml_escape(error)}</p>' if error else ""
    return f"""<!doctype html>
<title>Clara Agent - SMS Consent</title>
<h1>Text Message Consent</h1>
<p>Clara is a personal automation assistant that sends scheduled text message reminders
(calendar events and to-do items) to its owner's phone number.</p>
{error_html}
<form method="post" action="/consent">
  <label for="phone">Phone number</label><br>
  <input type="tel" id="phone" name="phone" placeholder="+15551234567" required><br><br>
  <label>
    <input type="checkbox" name="consent">
    I agree to receive automated SMS text messages from Clara, including calendar and
    to-do reminders. Message frequency varies. Message and data rates may apply.
    Reply STOP at any time to stop receiving messages, or HELP for help.
  </label><br><br>
  <button type="submit">Submit</button>
</form>
<p>See our <a href="/privacy">Privacy Policy</a> and <a href="/terms">Terms of Service</a>.</p>
"""


CONSENT_THANKYOU_HTML = """<!doctype html>
<title>Clara Agent - Thanks</title>
<h1>Thanks!</h1>
<p>You're opted in to receive text messages from Clara. Reply STOP at any time to stop
receiving messages, or HELP for help.</p>
"""

CONSENT_DECLINED_HTML = """<!doctype html>
<title>Clara Agent - Submitted</title>
<h1>Got it!</h1>
<p>Your submission was received. Since the SMS consent box wasn't checked, you have not
been opted in to receive text messages from Clara.</p>
"""

PRIVACY_POLICY_HTML = """<!doctype html>
<title>Clara Agent - Privacy Policy</title>
<h1>Privacy Policy</h1>
<p>Clara is a personal automation tool built and operated by a single individual for their
own private use. It is not offered as a public service and does not message, store data
about, or collect information from anyone other than its one configured owner/recipient.</p>
<h2>What data Clara accesses</h2>
<ul>
<li>The owner's Google Calendar, read-only.</li>
<li>The owner's Notion to-do list, to read items and mark them complete or add new ones.</li>
<li>The owner's phone number, to send and receive SMS text messages via Twilio.</li>
<li>The content of text messages exchanged with the owner, which is sent to Anthropic's
Claude API to interpret requests and draft replies.</li>
</ul>
<h2>What Clara does not do</h2>
<p>Clara does not sell, share, or use this data for advertising. It does not message anyone
other than its owner. It does not use the data for any purpose beyond running the owner's
personal scheduling reminders.</p>
<h2>Contact</h2>
<p>This tool has a single owner/operator; there is no separate public support channel.</p>
"""

TERMS_HTML = """<!doctype html>
<title>Clara Agent - Terms of Service</title>
<h1>Terms of Service</h1>
<p>Clara is a personal, single-user automation tool. It is built, owned, and operated by one
individual for their own private use, and is not offered to the general public.</p>
<h2>Messaging</h2>
<p>Clara sends scheduled text messages (morning, afternoon, and evening) to its owner's own
phone number, and replies to texts the owner sends it. Message and data rates may apply.
Reply STOP at any time to stop receiving messages, or HELP for help.</p>
<h2>No warranty</h2>
<p>Clara is provided as-is, for personal use only, with no guarantee of uptime or accuracy.</p>
"""


@app.post("/webhook/sms")
async def sms_webhook(request: Request):
    """
    Twilio hits this URL (form-encoded) whenever you text Clara.
    Configure this as your Twilio number's 'When a message comes in' webhook,
    e.g. https://<your-railway-domain>/webhook/sms
    """
    form = await request.form()
    incoming_text = form.get("Body", "").strip()
    from_number = form.get("From", "")

    # Basic safety: only respond to messages from your configured number.
    if settings.MY_PHONE_NUMBER and from_number != settings.MY_PHONE_NUMBER:
        log.warning("Ignoring message from unrecognized number: %s", from_number)
        return Response(content="<Response></Response>", media_type="application/xml")

    reply_text = handle_incoming_message(incoming_text)

    twiml = f"<Response><Message>{_xml_escape(reply_text)}</Message></Response>"
    return Response(content=twiml, media_type="application/xml")


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def handle_incoming_message(user_text: str) -> str:
    # Always pull the full open list fresh (not just today's/tomorrow's scheduled-job
    # subset) so on-demand questions about any date, and "mark N done", both resolve
    # correctly regardless of what the last scheduled message showed.
    fresh = notion_todo.get_all_open_todos()
    open_todos = [{"num": i + 1, **t} for i, t in enumerate(fresh)]
    db.save_last_list(open_todos)

    remaining_events = google_calendar.get_events_remaining_today()

    result = agent_brain.interpret_message(user_text, open_todos, remaining_events)
    intent = result.get("intent")

    if intent == "complete_item":
        for page_id in result.get("page_ids_to_complete", []):
            try:
                notion_todo.mark_item_done(page_id)
            except Exception as e:
                log.error("Failed to mark item done: %s", e)
        # Refresh cached list after completions
        fresh = notion_todo.get_all_open_todos()
        db.save_last_list([{"num": i + 1, **t} for i, t in enumerate(fresh)])

    elif intent == "add_item":
        title = result.get("new_item_title")
        due = result.get("new_item_due_date")
        if title:
            try:
                notion_todo.create_todo_item(title, due)
                fresh = notion_todo.get_all_open_todos()
                db.save_last_list([{"num": i + 1, **t} for i, t in enumerate(fresh)])
            except Exception as e:
                log.error("Failed to create item: %s", e)

    return result.get("reply", "Got it!")


# --- Manual trigger endpoints, useful for testing without waiting for the cron time ---

@app.post("/trigger/morning")
def trigger_morning():
    sched_module.morning_job()
    return {"status": "sent"}


@app.post("/trigger/afternoon")
def trigger_afternoon():
    sched_module.afternoon_job()
    return {"status": "sent"}


@app.post("/trigger/evening")
def trigger_evening():
    sched_module.evening_job()
    return {"status": "sent"}
