import os

class Settings:
    # --- Anthropic ---
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    CLARA_MODEL = os.environ.get("CLARA_MODEL", "claude-sonnet-5")

    # --- Twilio / SMS ---
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_SMS_FROM = os.environ.get("TWILIO_SMS_FROM", "")  # e.g. "+14155238886"
    MY_PHONE_NUMBER = os.environ.get("MY_PHONE_NUMBER", "")  # e.g. "+15551234567"

    # --- Google Calendar (read-only) ---
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN", "")
    GOOGLE_CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "primary")

    # --- Notion ---
    NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
    NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")
    # Property names in your Notion database (adjust to match your schema exactly)
    NOTION_TITLE_PROP = os.environ.get("NOTION_TITLE_PROP", "Name")
    NOTION_STATUS_PROP = os.environ.get("NOTION_STATUS_PROP", "Status")
    NOTION_DUE_DATE_PROP = os.environ.get("NOTION_DUE_DATE_PROP", "Due Date")
    NOTION_STATUS_TYPE = os.environ.get("NOTION_STATUS_TYPE", "status")  # "status" or "select"
    NOTION_NOT_DONE_VALUE = os.environ.get("NOTION_NOT_DONE_VALUE", "Not started")
    NOTION_DONE_VALUE = os.environ.get("NOTION_DONE_VALUE", "Done")

    # --- Database ---
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./clara.db")

    # --- Misc ---
    TIMEZONE = os.environ.get("TIMEZONE", "America/New_York")
    PORT = int(os.environ.get("PORT", "8080"))

settings = Settings()
