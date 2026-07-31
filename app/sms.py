from twilio.rest import Client
from app.config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _client


def send_message(body: str):
    client = _get_client()
    return client.messages.create(
        from_=settings.TWILIO_SMS_FROM,
        to=settings.MY_PHONE_NUMBER,
        body=body,
    )
