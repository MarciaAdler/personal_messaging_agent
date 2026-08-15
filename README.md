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
with toll-free verification instead) — this is not optional. Without an approved campaign,
Twilio will not reliably send your messages at all; there's no functional version of Clara
without it. For a single-recipient personal agent like Clara, Twilio's **Low Volume
Standard** 10DLC campaign is the right tier — it's a short self-serve form in the Twilio
Console (Messaging > Regulatory Compliance > Campaigns), no Meta/Facebook Business Manager
involved. Vetting can take 1-7 business days, so register this early
and expect to wait before Clara is usable end to end.

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
5. Register a **Brand** first (Messaging > Regulatory Compliance > Brand Registrations) —
   a Campaign can't be created without an approved Brand behind it. No EIN? Register a
   **Sole Proprietor** Brand: legal name, email, phone, address, and OTP verification via a
   real US/Canada mobile number (not VoIP). Costs about $4 one-time. Have an EIN? Register a
   **Standard** Brand instead.
6. Once the Brand is approved, register a **Low Volume Standard** A2P 10DLC campaign
   (Messaging > Regulatory Compliance > Campaigns) under it — this is the tier appropriate
   for a single-recipient personal agent like Clara (see "Carrier registration for SMS"
   above for why this step is required at all). It's a short form, not a Meta/Business
   verification process. See "A2P 10DLC campaign template" below for exact field values
   known to get approved.
7. Create a **Messaging Service** (Messaging > Services), add your number to its Sender Pool,
   and attach the approved Campaign to it under the service's Compliance tab. Registering a
   Brand/Campaign does *not* automatically attach it to your number — skipping this step
   causes sends to fail with error 30034 ("Message from an Unregistered Number") even after
   approval.

### A2P 10DLC campaign template

This app's own campaign was rejected three times before landing on the field values below:
once for the campaign description itself not meeting Twilio's content standards (it included
personal information — keep the description and sample messages strictly generic/functional,
describing what the app does and how consent works, not real personal details like your own
specific health/calendar content or anything else identifying beyond your name and the app's
purpose), once for using a mandatory consent checkbox (a checkbox that blocks form submission
if unchecked isn't a free opt-in choice), and once for sample messages that didn't include a
standard opt-out keyword. It took real trial and error to land on wording Twilio would
actually approve, so treat deviations from this template as a likely source of a fresh
rejection. The template below has all three fixed in, and matches what `/consent`,
`/privacy`, and `/terms` (already built into `app/main.py`) actually serve — fill in your own
values wherever you see `<PLACEHOLDER>`.

- **Brand type**: Sole Proprietor (no EIN) — or Standard, if you have an EIN.
- **Use case type**: `SOLE_PROPRIETOR` (the only option for a Sole Proprietor Brand). If you
  registered a Standard Brand instead, use `Mixed`.
- **Campaign description** (your legal name here is expected/required as the Sole
  Proprietor/Brand owner — it's the *other* personal details, like real calendar or health
  content, that got the earlier submission flagged):
  > `<YOUR_SOLE_PROPRIETOR_NAME>` operates `<YOUR_APP_NAME>`, an SMS-based personal
  > scheduling notification service. The service sends registered users automated
  > reminders based on their calendar and to-do list, including a morning daily summary,
  > an afternoon outstanding-items
  > reminder, and an evening preview of the next day. Users may reply by SMS to mark to-do
  > items complete, add new items, or request their current outstanding items. Users opt in
  > via a consent page at `https://<YOUR_RAILWAY_DOMAIN>/consent` prior to receiving
  > messages. This campaign is not used for marketing, sales, or promotional communications.
- **Sample messages** (at least one must include opt-out language like "Reply STOP"):
  1. > Good morning! Here is your day: Team standup at 10am, dentist at 2pm. Open to-dos:
     > 1) Finish Q3 report, due today. 2) Call plumber. 3) Buy milk. Reply STOP to opt out,
     > HELP for help. - `<YOUR_APP_NAME>`
  2. > Still outstanding today: 1) Finish Q3 report. Reply done 1 to mark it complete, or ask
     > what is on your plate. - `<YOUR_APP_NAME>`
  3. > Tomorrow preview: Flight at 7am, lunch with Sam at noon. - `<YOUR_APP_NAME>`
- **How do end-users opt in to receive messages?**
  > End-users opt in through a web form hosted at `https://<YOUR_RAILWAY_DOMAIN>/consent`.
  > On that page, the user enters their phone number and checks a consent checkbox stating:
  > "I agree to receive automated SMS text messages from `<YOUR_APP_NAME>`, including
  > calendar and to-do reminders. Message frequency varies. Message and data rates may
  > apply. Reply STOP at any time to stop receiving messages, or HELP for help." The
  > checkbox is optional to submit the form but required to actually opt in — leaving it
  > unchecked and submitting records no consent and sends no messages. Submitting with it
  > checked stores a timestamped consent record. The page also links to the Privacy Policy
  > and Terms of Service. This is a single-recipient personal application, so the only
  > person who will ever complete this opt-in is the application's own owner/operator.
- **Opt-in method**: Web Form.
- **Opt-out message**:
  > You have successfully been unsubscribed. You will not receive any more messages from
  > this number. Reply START to resubscribe.
- **Terms and conditions URL**: `https://<YOUR_RAILWAY_DOMAIN>/terms`
- **Privacy policy URL**: `https://<YOUR_RAILWAY_DOMAIN>/privacy`

The consent checkbox being optional-but-meaningful is enforced in code, not just described in
the form — see `_consent_form_html()` and `consent_submit()` in `app/main.py`. If you ever
add `required` back to that checkbox, the form will no longer match this campaign description
and risks a future rejection.

## Step 3: Google Calendar (read-only)

Run this part on your own computer, not on Railway, since it needs a one-time browser login.

1. Go to https://console.cloud.google.com/, create a project.
2. Enable the **Google Calendar API** (APIs & Services > Library).
3. Set up the OAuth consent screen. Google reshuffles this menu's exact location
   periodically, so rather than following a specific click-path, use the search bar at the
   top of the Cloud Console and search **"Audience"** (or "OAuth consent screen") to jump
   straight to it. Choose "External," fill in minimal info, and add your own Google account
   under "Test users."
4. **On that same Audience page, click "Publish App"** to move from "Testing" to "In
   production" status instead of leaving it in Testing. This matters more than it looks:
   Google hard-expires refresh tokens issued to Testing-mode apps after **7 days**, no
   matter how often they're used — Clara's scheduled jobs will silently start failing on
   Google Calendar every week if you skip this. Publishing to production for a read-only
   Calendar scope, with just yourself as a user, doesn't require Google's verification
   review — you may see an "unverified app" warning the next time you authorize, which is
   expected; click through it since it's your own app.

   **Do this before step 6 below, not after.** The 7-day expiry is baked into a token at the
   moment Google issues it — publishing to production only prevents the *next* token you
   generate from expiring, it does not retroactively fix a token you already have. If you
   generate your token first and publish afterward, that token is still on a 7-day clock.
5. Go to APIs & Services > Credentials > Create Credentials > OAuth client ID > "Desktop app."
   Download the JSON as `client_secret.json`.
6. On your computer: `pip install google-auth-oauthlib`, put `client_secret.json` in the
   `scripts/` folder, then run `python scripts/get_google_refresh_token.py`. Approve access
   in the browser window that opens.
7. Copy the printed `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN`
   into your Railway environment variables.

**If Calendar fetches ever start failing later** with `invalid_grant: Token has been expired
or revoked` in your Railway logs: first go back to the Audience page in Google Cloud Console
and confirm it still says "In production" (not "Testing" — Google can also revoke Testing
status in some cases, and if you ever created a fresh consent screen it defaults back to
Testing). Once you've confirmed production status, *then* rerun
`python scripts/get_google_refresh_token.py` for a fresh `GOOGLE_REFRESH_TOKEN` and update it
in Railway. Doing this in the other order (regenerating before confirming production status)
will leave you with another token that expires in 7 days.

## Step 4: Notion

1. Go to https://www.notion.so/my-integrations, create a new **internal integration**,
   copy its secret as `NOTION_API_KEY`.
2. Open your To-Do database in Notion → "..." menu → "Connect to" → select your integration.
3. Copy the database ID from the URL (`notion.so/yourspace/<DATABASE_ID>?v=...`) as
   `NOTION_DATABASE_ID`.
4. Run this locally to print your exact property names and status option values (this app
   doesn't auto-load `.env` for local scripts, so pass the two values inline):
   ```
   NOTION_API_KEY=<your key> NOTION_DATABASE_ID=<your database id> python3 scripts/inspect_notion_db.py
   ```
   Use that output to set `NOTION_TITLE_PROP`, `NOTION_STATUS_PROP`, `NOTION_DUE_DATE_PROP`,
   `NOTION_STATUS_TYPE`, `NOTION_NOT_DONE_VALUE`, and `NOTION_DONE_VALUE` precisely — they
   must match your database exactly. (These, and every other variable in this guide, still
   need to be set as real Railway env vars in Step 5 — filling in your local `.env` is just
   a staging copy for that.)

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
   `https://<your-railway-domain>/webhook/sms` (method: POST). Note: you can text Clara and
   the webhook will fire and generate a reply even before your A2P campaign is approved, but
   Twilio won't actually deliver that reply back to your phone until the campaign shows
   "Approved" — see the note under Step 2 above.

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

- This is built for a single user (you) — there's no multi-user auth.
- A2P 10DLC campaign approval (Step 2) can take anywhere from 1-7 business days, so budget
  time before your first scheduled message goes out reliably.
- If Notion's status property is type `select` rather than `status` in your database,
  set `NOTION_STATUS_TYPE=select` — the inspect script tells you which one you have.
