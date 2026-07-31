import datetime
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _get_service():
    creds = Credentials(
        token=None,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_events_for_date(target_date: datetime.date):
    """
    Returns a list of dicts: [{"summary": ..., "start": "9:00 AM", "end": "10:00 AM", "all_day": bool}]
    for the given local date, read-only.
    """
    tz = ZoneInfo(settings.TIMEZONE)
    start_of_day = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=tz)
    end_of_day = datetime.datetime.combine(target_date, datetime.time.max, tzinfo=tz)

    service = _get_service()
    events_result = (
        service.events()
        .list(
            calendarId=settings.GOOGLE_CALENDAR_ID,
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    formatted = []
    for e in events:
        start = e.get("start", {})
        end = e.get("end", {})
        summary = e.get("summary", "(No title)")
        if "dateTime" in start:
            start_dt = datetime.datetime.fromisoformat(start["dateTime"]).astimezone(tz)
            end_dt = datetime.datetime.fromisoformat(end["dateTime"]).astimezone(tz)
            formatted.append({
                "summary": summary,
                "start": start_dt.strftime("%-I:%M %p"),
                "end": end_dt.strftime("%-I:%M %p"),
                "all_day": False,
            })
        else:
            formatted.append({"summary": summary, "start": None, "end": None, "all_day": True})
    return formatted


def get_events_remaining_today():
    """Events later than right now, today, for the 'what's outstanding' query."""
    tz = ZoneInfo(settings.TIMEZONE)
    now = datetime.datetime.now(tz)
    all_today = get_events_for_date(now.date())
    # Filter out ones whose start time has already passed (all-day events always included)
    remaining = []
    for ev in all_today:
        if ev["all_day"]:
            remaining.append(ev)
            continue
        ev_start = datetime.datetime.strptime(ev["start"], "%I:%M %p").time()
        if ev_start >= now.time():
            remaining.append(ev)
    return remaining
