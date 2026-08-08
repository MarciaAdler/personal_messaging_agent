import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings, local_today
from app import google_calendar, notion_todo, agent_brain, sms, db

log = logging.getLogger("clara.scheduler")


def _numbered(todos):
    return [{"num": i + 1, **t} for i, t in enumerate(todos)]


def _safe_events(date):
    """Returns None (rather than raising) if Google Calendar is unreachable, so a
    calendar outage doesn't take down the whole scheduled message."""
    try:
        return google_calendar.get_events_for_date(date)
    except Exception as e:
        log.error("Failed to fetch calendar events for %s: %s", date, e)
        return None


def _safe_todos(due_date):
    """Returns None (rather than raising) if Notion is unreachable, so a Notion outage
    doesn't take down the whole scheduled message."""
    try:
        return notion_todo.get_open_todos(due_date=due_date)
    except Exception as e:
        log.error("Failed to fetch to-dos for %s: %s", due_date, e)
        return None


def _numbered_or_none(todos):
    return _numbered(todos) if todos is not None else None


def morning_job():
    today = local_today()
    events = _safe_events(today)
    numbered = _numbered_or_none(_safe_todos(today))
    if numbered is not None:
        db.save_last_list(numbered)
    message = agent_brain.compose_daily_message("morning", events, numbered)
    sms.send_message(message)
    log.info("Sent morning message")


def afternoon_job():
    today = local_today()
    numbered = _numbered_or_none(_safe_todos(today))
    if numbered is not None:
        db.save_last_list(numbered)
    message = agent_brain.compose_daily_message("afternoon", [], numbered)
    sms.send_message(message)
    log.info("Sent afternoon message")


def evening_job():
    tomorrow = local_today() + datetime.timedelta(days=1)
    events = _safe_events(tomorrow)
    numbered = _numbered_or_none(_safe_todos(tomorrow))
    if numbered is not None:
        db.save_last_list(numbered)
    message = agent_brain.compose_daily_message("evening", events, numbered)
    sms.send_message(message)
    log.info("Sent evening message")


def start_scheduler():
    scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)
    scheduler.add_job(morning_job, "cron", hour=8, minute=0, id="morning_job", replace_existing=True)
    scheduler.add_job(afternoon_job, "cron", hour=17, minute=0, id="afternoon_job", replace_existing=True)
    scheduler.add_job(evening_job, "cron", hour=21, minute=0, id="evening_job", replace_existing=True)
    scheduler.start()
    log.info("Scheduler started (timezone=%s)", settings.TIMEZONE)
    return scheduler
