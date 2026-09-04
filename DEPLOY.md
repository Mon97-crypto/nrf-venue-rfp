# Deploying this app

Two independent halves: get Resend able to send as you (Part 1), then get the
app onto Render with the key (Part 2). The tool is useful before either is done
— *Copy* and *Open in mail app* work with no configuration at all — so you can
start outreach today and switch on one-click sending later.

---

## Part 1 — Resend

### 1. Create the account
Sign up at [resend.com](https://resend.com). The free plan covers this project
comfortably: **3,000 emails/month, 100/day, one verified domain, 30-day log
retention**. The full shortlist is 18 venues × 2 nights = 36 emails.

### 2. Add a *sending subdomain*, not the root domain
**Domains → Add Domain →** enter `send.impactanalytics.co`.

> ⚠️ Use the `send.` subdomain. Resend asks for an **MX record** for bounce
> handling, and putting that on the root `impactanalytics.co` would collide with
> the MX records that deliver your actual company email. On a subdomain it is
> isolated and cannot affect the main mailbox.

Pick the region closest to your recipients (US East for New York venues).

### 3. Add the DNS records
Resend shows three records on the **Records** tab. Copy them **verbatim** into
your DNS host (whoever runs `impactanalytics.co` — Cloudflare, GoDaddy, Route 53,
or your IT team):

| Type | Name | Purpose |
|---|---|---|
| `MX` | `send` | Bounce and complaint handling |
| `TXT` | `send` | SPF — authorises Resend to send |
| `TXT` | `resend._domainkey` | DKIM — cryptographic signature |

Do not retype these by hand; the DKIM value is a long public key and one wrong
character fails verification silently.

### 4. Verify
Click **Verify DNS Records**. Most domains go green within 15 minutes;
propagation can take up to 24 hours. SPF/DKIM warnings during that window are
normal and clear themselves.

### 5. Create a scoped API key
**API Keys → Create API Key**

- Name: `ia-venue-rfp`
- Permission: **Sending access** (not Full access — this app only sends)
- Domain: restrict it to `send.impactanalytics.co`

Copy the `re_...` value immediately — Resend shows it exactly once. Treat it as
a password: it goes in Render's environment, never in git.

### 6. Tell IT, briefly
If `impactanalytics.co` publishes a DMARC policy, mention that a new sending
subdomain is live. SPF and DKIM both align to the organisational domain under
relaxed alignment, so a `p=reject` policy on the root will not bounce these —
but it is a courtesy that avoids a surprised security ticket.

### Sending before DNS verifies
Resend lets a brand-new account send from the shared address
`onboarding@resend.dev`, but **only to the email address you signed up with**.
That is enough to prove the plumbing works end to end. Set
`RESEND_FROM=onboarding@resend.dev`, send yourself one RFP, then switch to the
real address once the domain is green. Never point it at a venue while on that
address — it will not be delivered.

---

## Part 2 — Render

This repo holds exactly one app, so there is no ambiguity about what deploys:
the venue board is served at the **root** of whatever URL Render gives you.

**1.** Push this repo to GitHub (see the repo README if it is not up there yet).

**2.** [dashboard.render.com](https://dashboard.render.com) → **+ New** →
**Blueprint**.

**3.** Connect GitHub if needed, then **Connect** next to
`Mon97-crypto/nrf-venue-rfp`. If it is not listed, click *Configure account* and
grant Render access to it.

**4.** Render reads `render.yaml` and shows one web service — **nrf-venue-rfp**,
Docker runtime, Free plan. Name the Blueprint and confirm the branch is **main**.

**5.** It prompts for **`RESEND_API_KEY`** (the `sync: false` variable). Paste the
`re_...` key from Part 1, or leave it blank and add it later — the tool runs
without one, it just cannot send in-app.

**6. Deploy Blueprint.** The build takes roughly 60–90 seconds: this image is
Flask and gunicorn only, with no system packages to install.

**7.** Watch the **Logs** tab for gunicorn's `Booting worker with pid ...`, then
**Your service is live**.

**8.** Open the URL at the top of the service page —
`https://nrf-venue-rfp.onrender.com`, possibly with a random suffix if that name
is already taken globally.

### Adding the key later

If you skipped it in step 5: service → **Environment** → **Add Environment
Variable** → `RESEND_API_KEY` → **Save Changes**. Saving triggers a redeploy on
its own.

Note that Render ignores `sync: false` variables when *updating* an existing
Blueprint, so it will never prompt you again — the dashboard is the only way to
add it after creation.

### Redeploying

Pushes to `main` deploy automatically when **Auto-Deploy** is on
(Settings → Build & Deploy). Otherwise **Manual Deploy → Deploy latest commit**.

### Verify the deploy

1. Open the service URL. You should land straight on the venue board — 18 cards,
   no other app in the way.
2. Check the badge top-right: **“● Resend connected”** in green means the key is
   live. Amber means it is missing, or the deploy predates it.
3. Click **Send RFP** on any venue, change the To address to your own, and
   **Send via Resend**. Confirm it arrives, that Reply-To is
   `marketing@impactanalytics.co`, that the card flipped to *RFP sent*, and that
   the send appears in Resend's **Emails** log.

Only after that test should you send to an actual venue.

### If the build fails

| Symptom | Likely cause |
|---|---|
| Build fails at `pip install` | Transient network — **Manual Deploy → Deploy latest commit** |
| Deploy is live but the page 404s | Deployed commit predates the app — check the Events tab shows the right commit |
| Render created a differently-named service | The Blueprint picked up a different repo or branch — check Settings → Repository and Branch |

## Two limits of the free plan

**The service sleeps.** A free web service spins down after 15 minutes without
traffic and takes about a minute to wake. The first page load after a quiet
period is slow; nothing is lost.

**The tracker is not durable.** Free instances cannot mount a persistent disk,
so the SQLite file lives on ephemeral container storage and resets on every
deploy and every spin-down. Two ways to handle it:

- *Free:* click **Export tracker** whenever you have made meaningful updates.
  It downloads the whole thing — statuses, notes, send log — as JSON.
- *~$7/month:* upgrade to a Starter instance, then uncomment the `disk:` block
  and the `VENUE_DB_PATH` variable in `render.yaml` and redeploy. State then
  survives everything.

For a six-week booking cycle the free plan plus periodic exports is honestly
fine. Resend's own log is a second record of everything actually sent.

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| Badge still amber after deploy | `RESEND_API_KEY` not saved, or the deploy predates it — redeploy |
| `Resend returned 403` | Key is domain-scoped and `RESEND_FROM` is on a different domain |
| `Resend returned 422` | The `from` domain is not verified yet, or the address is malformed |
| Email sends but never arrives | Still on `onboarding@resend.dev`, which only delivers to your own account address |
| Statuses reset overnight | Expected on free — see the durability note above |
