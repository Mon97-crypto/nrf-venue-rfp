# Deploying this app

Nothing to configure before it is useful. **Send RFP** opens a prefilled Gmail
compose window in a new tab — no API key, no verified sending domain, no
outbound mail from the server at all. The mail leaves the sender's own mailbox,
so it threads normally, lands in their Sent folder, and replies come straight
back to them.

---

## Part 1 — Render



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

**5.** There is nothing to fill in — the Blueprint carries every value it needs.

**6. Deploy Blueprint.** The build takes roughly 60–90 seconds: this image is
Flask and gunicorn only, with no system packages to install.

**7.** Watch the **Logs** tab for gunicorn's `Booting worker with pid ...`, then
**Your service is live**.

**8.** Open the URL at the top of the service page —
`https://nrf-venue-rfp.onrender.com`, possibly with a random suffix if that name
is already taken globally.

### Redeploying

Pushes to `main` deploy automatically when **Auto-Deploy** is on
(Settings → Build & Deploy). Otherwise **Manual Deploy → Deploy latest commit**.

### Verify the deploy

1. Open the service URL. You should land straight on the venue board — 18 cards,
   no other app in the way.
2. Click **Send RFP** on any venue. A Gmail compose window should open in a new
   tab, addressed to the venue, with the subject and body filled in — and the
   card should flip to *RFP sent* behind it.
3. Close the Gmail tab without sending, then reload the board: the card should
   still read *RFP sent*, which confirms the tracker is persisting.

Then send one to yourself before sending to a venue.

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
fine — and your Gmail Sent folder is a second record of everything that went
out, independent of this app entirely.

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| Statuses reset overnight | Expected on free — see the durability note above |
| Gmail opens under the wrong account | Check `sending_account` in `senders.json`, or set `GMAIL_SENDING_ACCOUNT` |
| Gmail asks you to sign in | The sending account is not signed into that browser |
| Gmail opens with an empty To | The venue has no public address — it is a `form only` card; use their enquiry form |
