import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings
from app import google_calendar, notion_todo, agent_brain, sms, db

log = logging.getLogger("clara.scheduler")


def _numbered(todos):
    return [{"num": i + 1, **t} for i, t in enumerate(todos)]


def morning_job():
    today = datetime.date.today()
    events = google_calendar.get_events_for_date(today)
    todos = notion_todo.get_open_todos(due_on_or_before=today)
    numbered = _numbered(todos)
    db.save_last_list(numbered)
    message = agent_brain.compose_daily_message("morning", events, numbered)
    sms.send_message(message)
    log.info("Sent morning message")


def afternoon_job():
    todos = notion_todo.get_all_open_todos()
    numbered = _numbered(todos)
    db.save_last_list(numbered)
    message = agent_brain.compose_daily_message("afternoon", [], numbered)
    sms.send_message(message)
    log.info("Sent afternoon message")


def evening_job():
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    events = google_calendar.get_events_for_date(tomorrow)
    message = agent_brain.compose_daily_message("evening", events, [])
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
