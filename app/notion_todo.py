import datetime
import requests
from app.config import settings

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"


def _headers():
    return {
        "Authorization": f"Bearer {settings.NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _status_filter_not_done():
    prop_type = settings.NOTION_STATUS_TYPE
    return {
        "property": settings.NOTION_STATUS_PROP,
        prop_type: {"does_not_equal": settings.NOTION_DONE_VALUE},
    }


def get_open_todos(due_date: datetime.date = None):
    """
    Returns open (not-done) to-do items, optionally filtered to items due exactly on due_date.
    Each item: {"page_id": ..., "title": ..., "due_date": "YYYY-MM-DD" or None}
    """
    filters = [_status_filter_not_done()]
    if due_date:
        filters.append({
            "property": settings.NOTION_DUE_DATE_PROP,
            "date": {"equals": due_date.isoformat()},
        })

    payload = {"filter": {"and": filters}} if len(filters) > 1 else {"filter": filters[0]}

    resp = requests.post(
        f"{BASE_URL}/databases/{settings.NOTION_DATABASE_ID}/query",
        headers=_headers(),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return [_parse_page(p) for p in results]


def get_all_open_todos():
    """All open to-dos regardless of due date (used for on-demand queries, which filter by date themselves)."""
    return get_open_todos(due_date=None)


def _parse_page(page):
    props = page.get("properties", {})
    title_prop = props.get(settings.NOTION_TITLE_PROP, {})
    title = ""
    for t in title_prop.get("title", []):
        title += t.get("plain_text", "")

    due_prop = props.get(settings.NOTION_DUE_DATE_PROP, {})
    due_date = None
    date_obj = due_prop.get("date")
    if date_obj:
        due_date = date_obj.get("start")

    return {"page_id": page["id"], "title": title or "(untitled)", "due_date": due_date}


def mark_item_done(page_id: str):
    """Updates status to the configured 'done' value. Never deletes the page."""
    prop_type = settings.NOTION_STATUS_TYPE
    payload = {
        "properties": {
            settings.NOTION_STATUS_PROP: {
                prop_type: {"name": settings.NOTION_DONE_VALUE}
            }
        }
    }
    resp = requests.patch(f"{BASE_URL}/pages/{page_id}", headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def create_todo_item(title: str, due_date: str = None):
    """Creates a new to-do item. due_date should be 'YYYY-MM-DD' if provided."""
    properties = {
        settings.NOTION_TITLE_PROP: {"title": [{"text": {"content": title}}]},
        settings.NOTION_STATUS_PROP: {
            settings.NOTION_STATUS_TYPE: {"name": settings.NOTION_NOT_DONE_VALUE}
        },
    }
    if due_date:
        properties[settings.NOTION_DUE_DATE_PROP] = {"date": {"start": due_date}}

    payload = {
        "parent": {"database_id": settings.NOTION_DATABASE_ID},
        "properties": properties,
    }
    resp = requests.post(f"{BASE_URL}/pages", headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()
