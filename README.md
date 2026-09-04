# NRF 2027 venue RFPs

A shortlist of New York venues for the two evenings around
[NRF Retail's Big Show 2027](https://nrfbigshow.nrf.com/) (10–12 January, Javits
Center), and the outreach tooling to actually book one: per-venue RFP drafts,
one-click RFP drafts that open straight in Gmail, and status tracking.

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
- **Send RFP opens Gmail**, prefilled with the venue's address, subject and
  body, and marks the card *RFP sent*. Nothing is sent by the server — the mail
  goes from your own mailbox, so it threads normally and replies come back to
  you rather than to a service address.
- **Tracking** — Not contacted → RFP sent → Replied → Proposal → Shortlisted →
  Booked / Declined, with per-night progress and a JSON export.

## Running it locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py       # http://127.0.0.1:5000
```

No configuration needed at all — the Gmail hand-off works out of the box.

## Deploying

[DEPLOY.md](DEPLOY.md) is the full runbook for standing the service up on
Render from `render.yaml`.

## Configuration

All optional except the API key, and only for in-app sending.

| Variable | Default | Purpose |
|---|---|---|
| `RFP_SENDER_ORG` | `Impact Analytics` | Used in the subject and body |
| `GMAIL_ACCOUNT_INDEX` | _unset_ | Set to `0`, `1`… if Gmail opens under the wrong signed-in account |
| `RFP_SENDER_PHONE` | _unset_ | Added to the signature when set |
| `VENUE_DB_PATH` | `venue_rfp/data/outreach.db` | SQLite tracker location |

## Who RFPs are sent as

`venue_rfp/data/senders.json` holds the name, title and contact address used to
sign every RFP. The first entry is the one used.

```json
{ "senders": [
  { "id": "ab", "name": "A. Beckett", "title": "Director, Field Marketing",
    "from": "abeckett@impactanalytics.net", "reply_to": "abeckett@impactanalytics.co" }
]}
```

`reply_to` is the address printed in the signature. Since Gmail sends the mail,
the actual From line is whichever Google account is composing — this file only
controls how the RFP is signed. Delete the file, or leave it empty, and the tool
falls back to the environment variables above.

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
  mailer.py                   the generic RFP body + Gmail compose URLs
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
| `GET /api/draft/<venue>/<night>` | Prefilled to/subject/body plus the Gmail URL |
| `POST /api/outreach/<venue>/<night>` | Status and notes |
| `POST /api/meta/<venue>` | Cover image / email override |
| `GET /api/export` | Download the tracker as JSON |
