---
description: Interactively walk a new user through setting up their own Clara instance with their own credentials
---

You are guiding someone through setting up their own private instance of Clara (a personal
SMS scheduling agent) end to end: Anthropic, Twilio SMS + A2P registration, Google Calendar,
Notion, and deployment to Railway. This mirrors the steps in `README.md`, but interactively,
catching the specific mistakes people commonly make at each step.

**Ground rules for how you run this:**

- Go **one phase at a time**. Don't dump the whole checklist at once. Confirm each phase
  works before moving to the next.
- **Never ask the user to paste a raw secret value into the chat.** For anything sensitive
  (API keys, OAuth client secrets, refresh tokens), either have them run a command in their
  own terminal and read the output there, or have them open the local `.env` file directly in
  their editor and fill it in themselves. You can create/edit `.env` with placeholder blanks
  and instruct them what to fill in on which line, without ever seeing the value yourself.
- Detect their OS/shell before suggesting commands. On macOS, `python`/`pip` frequently
  don't exist as bare commands (only `python3`/`pip3`) -- check with `command -v python3` and
  `command -v pip3` before assuming, and use whichever the environment actually has.
- If something errors, don't guess blindly -- ask for the exact error text and reason from
  there. Most setup failures in this project have been one of a small set of known issues
  (listed at the bottom of this file) -- check those first before treating something as novel.
- At the end of each phase, append the collected non-secret config to a local `.env` file
  (git-ignored already) mirroring `.env.example`, so by the end the user has one file they
  can bulk-paste into Railway's Variables tab.

---

## Phase 0: Orientation

1. Confirm the user has cloned/opened this repo locally and has Python 3 installed
   (`command -v python3`). If not, point them to python.org or their OS package manager.
2. Copy `.env.example` to `.env` if `.env` doesn't already exist (this file is git-ignored --
   verify `.gitignore` covers it before proceeding).
3. Briefly explain the five services they'll need accounts for: Anthropic, Twilio, Google
   Cloud (Calendar API), Notion, and Railway. Ask if they already have accounts for any of
   these to skip redundant explanation.

## Phase 1: Anthropic API key

1. Have them create a key at https://console.anthropic.com/ (Settings -> API Keys).
2. **Important, easy to miss:** a fresh Anthropic account has no usable credit until a
   payment method is added. Tell them to go to Settings -> Billing and add a card / purchase
   credits *now*, even a small amount -- this project makes light API use, so $5-10 goes a
   long way. Skipping this causes a confusing "credit balance too low" error later that looks
   unrelated to setup.
3. Have them fill `ANTHROPIC_API_KEY` into their local `.env` themselves (don't ask them to
   paste the key into chat). Leave `CLARA_MODEL` as the default in `.env.example` unless they
   want a different model.

## Phase 2: Twilio + SMS

1. Sign up at https://www.twilio.com/try-twilio, buy an SMS-capable phone number.
2. Have them fill in `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` (from the Console home page),
   `TWILIO_SMS_FROM` (their new number, E.164 format e.g. `+15551234567`), and
   `MY_PHONE_NUMBER` (their own phone, same format) into `.env` themselves.
3. **Ask the user: do you have a business Tax ID / EIN for this?**
   - No EIN (most personal users): register a **Sole Proprietor** Brand under Messaging ->
     Regulatory Compliance in the Twilio Console. Needs legal name, email, phone, address,
     and OTP verification via a real US/Canada mobile number (not a VoIP number). Cost: ~$4
     one-time.
   - Has an EIN: register a **Standard** Brand, then a **Low Volume Standard** Campaign.
4. For the Campaign form, use the known-good template in the "A2P 10DLC campaign template"
   section of `README.md` -- it's the exact field wording (with placeholders swapped for
   this user's own name/app name/domain) that got this app's own campaign approved, after
   three earlier rejections. It took real trial and error to land on this wording, so treat
   deviations from the template as a likely source of a fresh rejection:
   - **Rejection 1**: the campaign description itself didn't meet Twilio's content
     standards -- it included personal information. Fixed by keeping the description and
     sample messages strictly generic/functional (what the app does, how consent works),
     not real personal details beyond the operator's name and the app's purpose.
   - **Rejection 2**: the consent checkbox on `/consent` was `required`, so the form
     couldn't be submitted without checking it -- Twilio reads that as consent not being a
     free choice. Fixed in code (`app/main.py`) -- the checkbox is now optional to submit
     but still required to actually opt in (unchecked submissions record no consent, send
     no SMS). Don't re-add `required` to that checkbox, or the campaign description (which
     now describes it as optional-to-submit) will stop matching actual behavior.
   - **Rejection 3**: none of the submitted sample messages included a standard opt-out
     keyword. Fixed by including "Reply STOP to opt out" in at least one sample message --
     the template's sample message #1 already has this baked in.
   - Use case type: `SOLE_PROPRIETOR` for a Sole Proprietor Brand, `Mixed` for a Standard
     Brand.
   - Opt-in method to check: **Web Form**, pointing at `https://<railway-domain>/consent`
     (the app already serves this page, backed by a real consent record in Postgres --
     see `app/main.py` / `app/db.py`). Fill in the real Railway domain once deployed
     (Phase 6) if not known yet.
   - Draft all free-text fields in plain ASCII (no em dashes, no smart quotes/curly
     apostrophes) -- these have caused silent-garbling validation failures before.
   - Privacy policy / terms links: `https://<railway-domain>/privacy` and `/terms`, which
     the app already serves (see `app/main.py`) -- fill in once Railway is deployed
     (Phase 6).
5. **Critical, commonly missed step:** registering a Brand and Campaign does NOT
   automatically attach them to the phone number. Create a **Messaging Service** (Console ->
   Messaging -> Services), add the number to its **Sender Pool**, and attach the approved
   Campaign to it under the service's Compliance tab. Without this, sends fail with error
   30034 ("Message from an Unregistered Number") even after the Campaign is approved.
6. Tell them vetting takes 1-7 business days, and campaign approval is **not optional** --
   Twilio won't reliably send any outbound message, scheduled or
   reply, from an unregistered number. They can continue with the rest of setup while
   waiting, but Clara won't be usable end to end until the campaign shows "Approved."

## Phase 3: Google Calendar (read-only)

Do this part on the user's own machine, not just describing it -- it needs their real
browser login.

1. https://console.cloud.google.com/ -> create a project.
2. **Enable the Calendar API explicitly**: APIs & Services -> Library -> search "Google
   Calendar API" -> Enable. (Easy to skip -- creating the project alone does NOT enable it,
   and the resulting error only surfaces later, mid-webhook-call, as a confusing 403.)
3. Configure the consent screen: in newer Cloud Console UI this is under **APIs & Services ->
   Google Auth Platform** (three tabs: Branding, Audience, Clients -- this replaced the old
   single-page "OAuth consent screen"). Under **Audience**, add the user's own Google account
   email as a **Test user**. Being the project owner does NOT substitute for this -- it's a
   separate explicit list Google checks regardless of IAM role.
4. Under Clients, create an OAuth client ID, type "Desktop app," download the JSON.
5. Have the user save it as `scripts/client_secret.json` (any filename works since
   `get_google_refresh_token.py` resolves the path relative to its own location, but this
   name matches what's git-ignored already via `scripts/client_secret*.json`).
6. Run (or have them run) from repo root: `pip3 install -r requirements.txt` if not already
   done, then have **the user themselves** run `python3 scripts/get_google_refresh_token.py`
   in their own terminal -- it opens a real browser for login and prints
   `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`/`GOOGLE_REFRESH_TOKEN` to their terminal, not the
   browser. Have them copy those three into `.env` themselves.
7. If they get `Error 403: access_denied` / "has not completed verification": they weren't
   added as a Test user in the right project, or logged in with a different Google account
   than the one they added -- send them back to step 3.

## Phase 4: Notion

1. https://www.notion.so/my-integrations -> create an internal integration -> copy the
   secret into `.env` as `NOTION_API_KEY` (user does this themselves).
2. Open their To-Do database in Notion -> `...` menu -> **Connect to** -> select the
   integration. **This step is commonly skipped or done on the wrong object** -- if the To-Do
   list is an inline table embedded in a page rather than its own full-page database, expand
   it to full-page view first, since the URL/ID of the containing page won't work.
3. Copy the database ID from the URL into `.env` as `NOTION_DATABASE_ID`.
4. Run: `NOTION_API_KEY=... NOTION_DATABASE_ID=... python3 scripts/inspect_notion_db.py`
   (their own real values inline, not placeholders) to print property names and status/select
   option values.
5. A 404 here almost always means step 2 (Connect to) wasn't done for that exact database, or
   the ID is a page ID rather than the database's own ID -- not a wrong secret.
6. Map the script's output into `NOTION_TITLE_PROP`, `NOTION_STATUS_PROP`,
   `NOTION_DUE_DATE_PROP`, `NOTION_STATUS_TYPE`, `NOTION_NOT_DONE_VALUE`, `NOTION_DONE_VALUE`
   in `.env`, matching their database exactly.

## Phase 5: Review the .env file

Read back `.env` (values redacted/not printed if you want to avoid echoing secrets into the
transcript -- just confirm which keys are filled vs. still blank) and confirm every variable
in `.env.example` has a value before moving to deployment.

## Phase 6: Deploy to Railway

1. Push the repo to GitHub. If it's a **private repo** and Railway's "Deploy from GitHub
   repo" doesn't find it: the Railway GitHub App needs explicit access -- go to
   github.com/settings/installations -> Railway App -> Configure -> grant access to this repo
   (or the whole org, if it lives under one -- org repos need the app installed at the org
   level specifically).
2. New Railway project -> Deploy from that GitHub repo.
3. Add a **Postgres** plugin. Then, in the **app service's** Variables tab (not the Postgres
   service), add `DATABASE_URL` as a **reference** (not a literal value) pointing at
   `${{Postgres.DATABASE_URL}}` -- Railway does NOT auto-inject plugin variables into other
   services anymore; this must be added explicitly via "Add Reference."
4. Paste in every other variable from the local `.env`.
5. Generate a **public** (not private) networking domain, HTTP, and give it port `8080` when
   asked -- Railway will set `PORT=8080` for the container to match, and the app's `Procfile`
   already binds to `$PORT` dynamically.
6. Once live, go back to Twilio: set the number's (or Messaging Service's) "when a message
   comes in" webhook to the **full URL** `https://<railway-domain>/webhook/sms`, method POST
   -- the path alone isn't enough, Twilio needs the whole domain. Note: the webhook will
   fire and Clara will generate a reply even before the A2P campaign is approved, but Twilio
   won't actually deliver that reply back to the user's phone until the campaign shows
   "Approved" -- don't mistake a missing reply for a broken webhook while waiting on
   approval.
7. Fill the real Railway domain into the privacy/terms links in the Twilio Campaign form from
   Phase 2 if not already done.

## Phase 7: Test end to end

1. Confirm the A2P campaign shows "Approved" in the Twilio Console before expecting any
   outbound send (reply or scheduled) to reliably deliver -- this isn't optional, see
   Phase 2.
2. Text the Twilio number something like "what's outstanding?" -- should get a real reply
   using live Notion + Calendar data.
3. Manually fire scheduled jobs without waiting for the actual time:
   `curl -X POST https://<railway-domain>/trigger/morning` (and `/trigger/afternoon`,
   `/trigger/evening`).
4. If sends fail even with an approved campaign, check that the Messaging
   Service/Sender Pool/Compliance attachment from Phase 2 step 5 was actually done --
   that's the other common cause of silent send failures post-approval.

---

## Known issues already fixed in this codebase (shouldn't recur, but check if they do)

- `psycopg2-binary` used to crash on Railway with `libpq.so.5: cannot open shared object
  file` -- fixed by switching to the pure-Python `pg8000` driver (`requirements.txt`,
  `app/db.py`). If someone reverts this, that error will come back.
- `CLARA_MODEL` default used to be an invalid model string (`claude-sonnet-4-6`) that doesn't
  exist -- fixed to a real model ID in `app/config.py`. If a user overrides `CLARA_MODEL` in
  their own env with a typo'd model name, `agent_brain.interpret_message` now degrades
  gracefully instead of 500ing (it catches the error and logs `interpret_message failed: ...`
  instead of crashing the webhook), so check Railway logs for that exact line if replies come
  back generic/confused.
- `get_google_refresh_token.py` used to hardcode a relative `client_secret.json` path that
  broke depending on which directory you ran it from -- fixed to resolve relative to the
  script's own location.
- A2P 10DLC campaign got rejected three times before approval: once because the campaign
  description itself included personal information and didn't meet Twilio's content
  standards, once because the `/consent` checkbox was `required` (blocked form submission
  unless checked -- not a free opt-in choice), and once because no submitted sample message
  included opt-out language ("Reply STOP"). All three are fixed in code and in the campaign
  template in `README.md` -- see Phase 2 above. It took real trial and error to land on
  wording Twilio would approve, so if a user's own resubmission gets rejected again, it
  likely means they deviated from that template.
