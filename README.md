# Clara — your SMS scheduling agent

Clara reads your Google Calendar (read-only) and Notion to-do list, texts you a morning
briefing at 8am ET, an outstanding-items check at 5pm ET, and a tomorrow-preview at 9pm ET.
You can message her anytime to mark items done, add new items, or ask what's outstanding.

**Guardrails built in:** Clara can never edit or delete calendar events (read-only scope),
and can never delete to-do items — only add new ones or flip their status to done.

**Setting this up for yourself?** If you're using [Claude Code](https://claude.com/claude-code),
open this repo and run `/setup` for an interactive, step-by-step walkthrough that catches the
common mistakes below as they happen. Otherwise, follow the steps manually below.

---

## Important thing to understand up front: carrier registration for SMS

Plain SMS has none of WhatsApp's Business/Meta verification or template-approval process —
that's the whole reason to use it instead. But US carriers do require Twilio numbers sending
application-generated text to register under **A2P 10DLC** (or use a **toll-free number**
with toll-free verification instead) before messages reliably deliver at scale. For a
single-recipient personal agent like Clara, Twilio's **Low Volume Standard** 10DLC campaign
is the right tier — it's a short self-serve form in the Twilio Console (Messaging > Regulatory
Compliance > Campaigns), no Meta/Facebook Business Manager involved, and typically approved
within a day. Skipping it won't necessarily block messages immediately, but expect filtering
or delivery issues over time, so budget a few minutes for this before relying on the scheduled
pings.

---

## Step 1: Anthropic API key

1. Go to https://console.anthropic.com/ and create an API key.
2. Save it — you'll set it as `ANTHROPIC_API_KEY` in Railway.

## Step 2: Twilio + SMS

1. Sign up at https://www.twilio.com/try-twilio.
2. Buy a phone number with SMS capability (Phone Numbers > Buy a number), or use a trial
   number to start.
3. From the Twilio Console home page, copy your **Account SID** and **Auth Token** — you'll
   set these as `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` in Railway (Step 5).
4. Note your Twilio number as `TWILIO_SMS_FROM` (format `+1XXXXXXXXXX`) and your own phone
   number as `MY_PHONE_NUMBER` (same format) — also set as Railway variables in Step 5.
5. Register a **Low Volume Standard** A2P 10DLC campaign (Messaging > Regulatory Compliance
   > Campaigns) so scheduled messages deliver reliably — see the note above. This is a
   short form, not a Meta/Business verification process.

## Step 3: Google Calendar (read-only)

Run this part on your own computer, not on Railway, since it needs a one-time browser login.

1. Go to https://console.cloud.google.com/, create a project.
2. Enable the **Google Calendar API** (APIs & Services > Library).
3. Go to APIs & Services > OAuth consent screen. Choose "External," fill in minimal info,
   and add your own Google account under "Test users." (Staying in "Testing" mode is fine
   — no Google review needed for personal use.)
4. Go to APIs & Services > Credentials > Create Credentials > OAuth client ID > "Desktop app."
   Download the JSON as `client_secret.json`.
5. On your computer: `pip install google-auth-oauthlib`, put `client_secret.json` in the
   `scripts/` folder, then run `python scripts/get_google_refresh_token.py`. Approve access
   in the browser window that opens.
6. Copy the printed `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN`
   into your Railway environment variables.

## Step 4: Notion

1. Go to https://www.notion.so/my-integrations, create a new **internal integration**,
   copy its secret as `NOTION_API_KEY`.
2. Open your To-Do database in Notion → "..." menu → "Connect to" → select your integration.
3. Copy the database ID from the URL (`notion.so/yourspace/<DATABASE_ID>?v=...`) as
   `NOTION_DATABASE_ID`.
4. Run `python scripts/inspect_notion_db.py` locally (set `NOTION_API_KEY` and
   `NOTION_DATABASE_ID` as env vars first) to print your exact property names and status
   option values. Use that output to set `NOTION_TITLE_PROP`, `NOTION_STATUS_PROP`,
   `NOTION_DUE_DATE_PROP`, `NOTION_STATUS_TYPE`, `NOTION_NOT_DONE_VALUE`, and
   `NOTION_DONE_VALUE` precisely — they must match your database exactly.

## Step 5: Deploy to Railway

1. Push this project to a GitHub repo (or use Railway's CLI to deploy directly from this
   folder).
2. In Railway, "New Project" → "Deploy from GitHub repo" (or `railway up` from this folder).
3. Add a **Postgres** plugin to the project (Railway sets `DATABASE_URL` automatically) —
   recommended over SQLite so your data persists across redeploys.
4. In your service's "Variables" tab, add every variable listed in `.env.example`, filled in
   with your real values from Steps 1-4 (leave `DATABASE_URL` unset if you added the Postgres
   plugin in step 3 above -- Railway sets it for you).
5. Once deployed, Railway gives you a public URL like `https://clara-production.up.railway.app`.
6. In Twilio, set your phone number's "When a message comes in" webhook to:
   `https://<your-railway-domain>/webhook/sms` (method: POST).

## Step 6: Test it

- Text your Twilio number something like "what's outstanding?" — Clara should reply using
  live Notion + Calendar data.
- Hit `POST https://<your-domain>/trigger/morning` (e.g. via curl or Postman) to manually
  fire the morning message without waiting for 8am, and similarly `/trigger/afternoon` and
  `/trigger/evening`.
- Once you're happy, the APScheduler jobs will run automatically at 8am / 5pm / 9pm
  America/New_York.

---

## How the conversation logic works

- Clara keeps a lightweight record (in Postgres) of the last numbered to-do list she showed
  you, so replies like "mark 2 done" resolve correctly.
- Every incoming message is sent to Claude along with your current open to-dos and today's
  remaining calendar events; Claude classifies your intent (complete / add / query / chat)
  and drafts the reply.
- Completions and additions go straight to Notion via its API. Calendar is queried live and
  never written to.

## Customizing message tone/content

Edit the prompts in `app/agent_brain.py` (`SYSTEM_PROMPT` and `compose_daily_message`) to
change Clara's tone or the exact format of her daily messages.

## Limitations to know about

- This is built for a single user (you) — there's no multi-user auth, which matches what
  you asked for.
- A2P 10DLC campaign approval (Step 2) can take anywhere from minutes to a day or two, so
  budget a little time before your first scheduled message goes out reliably.
- If Notion's status property is type `select` rather than `status` in your database,
  set `NOTION_STATUS_TYPE=select` — the inspect script tells you which one you have.
