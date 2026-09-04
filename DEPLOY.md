# Deploying this app

Two independent halves: get Resend able to send as you (Part 1), then get the
app onto Render with the key (Part 2). The tool is useful before either is done
— *Copy* and *Open in mail app* work with no configuration at all — so you can
start outreach today and switch on one-click sending later.

---

## Part 1 — Resend

`impactanalytics.net` is already verified in this Resend account, so domain
setup is done. Two things remain: pick the sending address, and mint a key.

### 1. Pick the From address

Any local part on the verified domain works — Resend does not require the
mailbox to exist. The default this repo ships is:

```
Impact Analytics Events <events@impactanalytics.net>
```

Change it with the `RESEND_FROM` variable if you would rather use
`marketing@impactanalytics.net` or similar.

> **The sending domain and your inbox are different domains.** Mail goes out as
> `@impactanalytics.net` (verified for sending) while replies come back to
> `marketing@impactanalytics.co` (where you actually read mail). That is set by
> `RFP_REPLY_TO` and is perfectly normal — Reply-To is only a header, and it has
> no bearing on SPF, DKIM or DMARC, which all authenticate against the From
> domain.
>
> One consequence worth knowing: a venue that hits *Reply* lands in your `.co`
> inbox correctly, but **bounces and out-of-office notices go to the From
> address**. If nobody monitors `events@impactanalytics.net`, you will not see a
> bad-address bounce. Either make it a real monitored mailbox or alias, or check
> Resend's **Emails** log — it records bounces regardless.

### 2. Create a scoped API key

**API Keys → Create API Key**

- Name: `ia-venue-rfp`
- Permission: **Sending access** — not Full access; this app only sends
- Domain: restrict it to **impactanalytics.net**

Copy the `re_...` value immediately; Resend shows it exactly once. It goes into
Render's environment in Part 2, never into git.

> If the key is scoped to a domain and `RESEND_FROM` is on a different one,
> every send fails with a `403`. That mismatch is the most common configuration
> error here.

### 3. Check the plan headroom

The free plan allows **3,000 emails/month and 100/day**, with one verified
domain. The full shortlist is 18 venues × 2 nights = 36 emails, so a single
day's outreach fits comfortably. If `impactanalytics.net` is already sending
production mail through this same Resend account, check the daily figure before
a bulk send.

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
| `Resend returned 422` | `RESEND_FROM` is malformed, or its domain is not `impactanalytics.net` |
| `Resend returned 429` | Daily cap (100 on the free plan) reached — resume tomorrow or upgrade |
| Badge shows the wrong From address | `RESEND_FROM` overridden in the Render dashboard; dashboard values beat `render.yaml` |
| Replies go missing | Check `RFP_REPLY_TO` on the badge — it should read `marketing@impactanalytics.co` |
| No bounce ever appears | Bounces go to the From address, not Reply-To — read them in Resend's **Emails** log |
| Statuses reset overnight | Expected on free — see the durability note above |
