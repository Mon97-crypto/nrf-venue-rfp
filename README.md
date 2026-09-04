# NRF 2027 venue RFPs

A shortlist of New York venues for the two evenings around
[NRF Retail's Big Show 2027](https://nrfbigshow.nrf.com/) (10–12 January, Javits
Center), and the outreach tooling to actually book one: per-venue RFP drafts,
one-click sending through [Resend](https://resend.com), and status tracking.

| Night | Date | Format | Headcount |
|---|---|---|---|
| Saturday reception | Sat 9 Jan 2027 | Standing cocktail, passed food | up to 50 |
| Sunday exec dinner | Sun 10 Jan 2027 | Seated, private or fully partitioned room | 30–35 |

18 venues are shortlisted, ranked by walking distance from the Javits Center.

## What it does

- **Venue cards** — capacity, neighbourhood, distance from Javits, and the
  events address, tagged `verified` / `form-only` / `unconfirmed` so you know
  which venues need their web form instead of an email.
- **Per-venue, per-night RFP drafts.** The asks differ by format: a reception
  brief asks about bar positions, canapé counts and coat check; a dinner brief
  asks about full-room privacy, table layout and AV. Editable before sending.
- **One-click send** through Resend, logged, flipping the venue to *RFP sent*.
  Without an API key the draft still copies to the clipboard or opens in your
  mail client, so the tool is useful before any setup.
- **Tracking** — Not contacted → RFP sent → Replied → Proposal → Shortlisted →
  Booked / Declined, with per-night progress and a JSON export.

## Running it locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py       # http://127.0.0.1:5000
```

No configuration needed to browse and draft. To send from inside the app, set
`RESEND_API_KEY` — see [DEPLOY.md](DEPLOY.md).

## Deploying

[DEPLOY.md](DEPLOY.md) is the full runbook: verifying a sending domain in
Resend, and standing the service up on Render from `render.yaml`.

## Configuration

All optional except the API key, and only for in-app sending.

| Variable | Default | Purpose |
|---|---|---|
| `RESEND_API_KEY` | _unset_ | Enables the "Send via Resend" button |
| `RESEND_FROM` | `Impact Analytics Events <events@impactanalytics.co>` | Must be a domain verified in Resend |
| `RFP_REPLY_TO` | `marketing@impactanalytics.co` | Reply-to, and the address in the signature |
| `RFP_SENDER_NAME` | `Impact Analytics — Events Team` | Signature name |
| `RFP_SENDER_ORG` | `Impact Analytics` | Used in the subject and body |
| `RFP_SENDER_PHONE` | _unset_ | Added to the signature when set |
| `VENUE_DB_PATH` | `venue_rfp/data/outreach.db` | SQLite tracker location |

## Editing the shortlist

`venue_rfp/data/venues.json` holds the event brief and the venue records.
`email_confidence` is one of:

- `verified` — published by the venue or its hospitality group
- `form_only` — no public address; use their enquiry form, or paste one into the
  card once you have it
- `unconfirmed` — an address exists but is a general line, not the events desk

Cover images and email addresses edited in the UI are stored in SQLite and
override the JSON, so the data file stays the clean source of record.

## Layout

```
app.py                        Flask entrypoint; mounts the blueprint at /
venue_rfp/
  blueprint.py                routes
  mailer.py                   RFP composition + Resend delivery (stdlib urllib)
  store.py                    SQLite tracker
  data/venues.json            the brief and the shortlist
  templates/venues.html       the whole UI
render.yaml  Dockerfile       deployment
```

The blueprint declares `/venues` so it can be sub-mounted on another Flask app;
`app.py` overrides that to the root. Front-end URLs are derived from the mount
point, so both work.

## Routes

| Route | Purpose |
|---|---|
| `GET /` | The board |
| `GET /api/venues` | Catalog merged with tracker state |
| `GET /api/draft/<venue>/<night>` | Prefilled to/subject/body |
| `POST /api/send` | Send via Resend, log it, mark as sent |
| `POST /api/outreach/<venue>/<night>` | Status and notes |
| `POST /api/meta/<venue>` | Cover image / email override |
| `GET /api/history` | Send log |
| `GET /api/export` | Download the tracker as JSON |
