"""
Run this ONCE locally to print out your Notion To-Do database's property names
and the exact option values for your status field. Use the output to set
NOTION_TITLE_PROP, NOTION_STATUS_PROP, NOTION_DUE_DATE_PROP, NOTION_STATUS_TYPE,
NOTION_NOT_DONE_VALUE, and NOTION_DONE_VALUE correctly in your Railway env vars.

Setup:
1. Go to https://www.notion.so/my-integrations and create a new internal integration.
   Copy its "Internal Integration Secret" -- this is your NOTION_API_KEY.
2. Open your To-Do database in Notion, click "..." > "Connect to" > select your
   new integration, so it's allowed to access that specific database.
3. Copy the database ID from its URL:
   https://www.notion.so/yourworkspace/<DATABASE_ID>?v=...
4. pip install requests
5. Run: NOTION_API_KEY=secret_xxx NOTION_DATABASE_ID=xxx python inspect_notion_db.py
"""

import os
import requests

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

resp = requests.get(
    f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}",
    headers={
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
    },
    timeout=15,
)
resp.raise_for_status()
data = resp.json()

print(f"\nDatabase title: {data.get('title', [{}])[0].get('plain_text', '(untitled)')}\n")
print("Properties found:\n")

for name, prop in data.get("properties", {}).items():
    ptype = prop.get("type")
    print(f"- \"{name}\"  (type: {ptype})")
    if ptype == "status":
        options = prop.get("status", {}).get("options", [])
        print(f"    status options: {[o['name'] for o in options]}")
    elif ptype == "select":
        options = prop.get("select", {}).get("options", [])
        print(f"    select options: {[o['name'] for o in options]}")

print("\nMap these into your Railway env vars, e.g.:")
print("  NOTION_TITLE_PROP=Name")
print("  NOTION_STATUS_PROP=Status")
print("  NOTION_DUE_DATE_PROP=Due Date")
print("  NOTION_STATUS_TYPE=status   (or 'select', matching the type printed above)")
print("  NOTION_NOT_DONE_VALUE=Not started")
print("  NOTION_DONE_VALUE=Done")
