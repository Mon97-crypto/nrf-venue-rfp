"""RFP body generation and Resend delivery.

Resend is called over plain urllib so the tool adds no new dependency. When
RESEND_API_KEY is unset the UI still composes and copies the RFP — it just
cannot send it.
"""
import json
import os
import urllib.error
import urllib.request

RESEND_ENDPOINT = 'https://api.resend.com/emails'
_SENDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'senders.json')


def senders():
    """The identities an RFP may be sent as.

    Read from data/senders.json. If that is missing or empty the environment
    variables below define a single sender, which is the original behaviour.
    """
    try:
        with open(_SENDERS_FILE, 'r', encoding='utf-8') as fh:
            entries = json.load(fh).get('senders') or []
    except (OSError, ValueError):
        entries = []

    out = []
    for e in entries:
        if not (e.get('id') and e.get('from')):
            continue
        out.append({
            'id': e['id'],
            'name': e.get('name', ''),
            'title': e.get('title', ''),
            'from': e['from'],
            'reply_to': e.get('reply_to', ''),
        })
    if out:
        return out

    return [{
        'id': 'default',
        'name': os.environ.get('RFP_SENDER_NAME', 'Impact Analytics — Events Team'),
        'title': os.environ.get('RFP_SENDER_TITLE', ''),
        'from': os.environ.get('RESEND_FROM', 'Impact Analytics Events <events@impactanalytics.net>'),
        'reply_to': os.environ.get('RFP_REPLY_TO', 'marketing@impactanalytics.co'),
    }]


def resolve_sender(sender_id=None):
    """Look a sender up by id. Never trust a client-supplied address — the
    caller passes an id and the From line comes from this list."""
    options = senders()
    if sender_id:
        for s in options:
            if s['id'] == sender_id:
                return s
    return options[0]


def config(sender_id=None):
    s = resolve_sender(sender_id)
    # A bare address gets the sender's name attached so the From line reads as
    # a person rather than a mailbox.
    from_address = s['from'] if '<' in s['from'] else (
        f"{s['name']} <{s['from']}>" if s['name'] else s['from'])
    return {
        'api_key': os.environ.get('RESEND_API_KEY', ''),
        'sender_id': s['id'],
        'from_address': from_address,
        # Reply-To is only a header, so it can be a mailbox on another domain.
        'reply_to': s['reply_to'],
        'sender_name': s['name'],
        'sender_title': s['title'],
        'sender_org': os.environ.get('RFP_SENDER_ORG', 'Impact Analytics'),
        'sender_phone': os.environ.get('RFP_SENDER_PHONE', ''),
    }


def is_configured():
    return bool(config()['api_key'])


def build_subject(venue, night, sender_id=None):
    return (
        f"Private event enquiry — {night['date']} · "
        f"{night['headcount']} · {config(sender_id)['sender_org']}"
    )


_ASKS_COMMON = [
    "Availability on the date above, and the largest hold you can place while we confirm",
    "Food & beverage minimum and/or room fee — and whether NRF week carries a premium",
    "Beverage packages, including a substantial non-alcoholic selection",
    "Deposit schedule, payment terms and the cancellation policy",
    "Dietary accommodation — we expect vegetarian, vegan, halal and gluten-free guests",
    "Whether service charge, administrative fee and tax are included in the quoted figures",
]

_ASKS_SEATED = [
    "Confirmation that the room is fully private, with no other diners seated in it",
    "Menu formats you would recommend at this headcount — set menu, family style or tasting",
    "AV: screen or projector, and a microphone for a short five-minute welcome",
    "Room layout options — one long table versus rounds — and your recommendation for conversation",
]

_ASKS_RECEPTION = [
    "Confirmation the space holds this many guests standing, comfortably rather than at capacity",
    "Passed canapé and station options, and how many pieces per guest you would advise",
    "Bar setup — number of bar positions and staffing for a group this size",
    "Coat check, and whether guests can arrive across a window rather than all at once",
    "Background music or a sound system we could plug into, and whether a short welcome is workable",
]


def build_body(venue, night, event, sender_id=None):
    cfg = config(sender_id)
    space = venue.get('space') or 'your private dining space'
    is_reception = 'reception' in night['format'].lower() or night['id'] == 'saturday'
    asks = _ASKS_COMMON[:1] + (_ASKS_RECEPTION if is_reception else _ASKS_SEATED) + _ASKS_COMMON[1:]

    lines = [
        f"Hello {venue['name']} events team,",
        "",
        f"I'm writing from {cfg['sender_org']} about a private event during "
        f"{event['name']} week in January ({event['conference_dates']}, Javits Center).",
        "",
        f"  Event      {night['format']}",
        f"  Date       {night['date']}",
        f"  Guests     {night['headcount']}",
        f"  Timing     approximately {night['window']}",
        f"  Space      {space}",
        "",
        f"The group is {night['audience']}.",
        "",
        "Could you please come back to me on the following:",
        "",
    ]
    lines += [f"  {i}. {ask}" for i, ask in enumerate(asks, start=1)]
    lines += [
        "",
        "We are comparing a short list of venues over the next two weeks and will "
        "move quickly once we have proposals in hand. A PDF pack or a call both work — "
        "whichever is easier for you.",
        "",
        "Thank you,",
        cfg['sender_name'],
        # "Director of Events, Impact Analytics" when a title is set, else the
        # organisation on its own.
        f"{cfg['sender_title']}, {cfg['sender_org']}" if cfg['sender_title'] else cfg['sender_org'],
    ]
    if cfg['sender_phone']:
        lines.append(cfg['sender_phone'])
    lines.append(cfg['reply_to'])
    return "\n".join(lines)


def send(to_email, subject, body, reply_to=None, sender_id=None):
    """Send via Resend. Returns (ok, message_id, error)."""
    cfg = config(sender_id)
    if not cfg['api_key']:
        return False, '', 'RESEND_API_KEY is not set on this deployment.'
    payload = {
        'from': cfg['from_address'],
        'to': [to_email],
        'subject': subject,
        'text': body,
    }
    reply = reply_to or cfg['reply_to']
    if reply:
        payload['reply_to'] = reply

    req = urllib.request.Request(
        RESEND_ENDPOINT,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f"Bearer {cfg['api_key']}",
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8') or '{}')
        return True, data.get('id', ''), ''
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')[:400]
        return False, '', f'Resend returned {exc.code}: {detail}'
    except Exception as exc:  # network, timeout, bad JSON
        return False, '', f'{type(exc).__name__}: {exc}'
