"""RFP composition and Gmail hand-off.

There is one generic RFP body. It is parameterised by venue and by night, so a
reception brief and a dinner brief differ in their details rather than in their
structure. Nothing is sent from this app: each draft becomes a prefilled Gmail
compose URL, so the mail leaves the sender's own mailbox, threads normally, and
lands in their Sent folder.
"""
import json
import os
import urllib.parse

GMAIL_COMPOSE = 'https://mail.google.com/mail/'
_SENDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'senders.json')


def senders():
    """The identities an RFP can be signed as (first entry is the default)."""
    try:
        with open(_SENDERS_FILE, 'r', encoding='utf-8') as fh:
            entries = json.load(fh).get('senders') or []
    except (OSError, ValueError):
        entries = []

    out = [
        {
            'id': e['id'],
            'name': e.get('name', ''),
            'title': e.get('title', ''),
            'reply_to': e.get('reply_to', ''),
        }
        for e in entries if e.get('id')
    ]
    if out:
        return out

    return [{
        'id': 'default',
        'name': os.environ.get('RFP_SENDER_NAME', 'Impact Analytics — Events Team'),
        'title': os.environ.get('RFP_SENDER_TITLE', ''),
        'reply_to': os.environ.get('RFP_REPLY_TO', 'marketing@impactanalytics.co'),
    }]


def resolve_sender(sender_id=None):
    options = senders()
    if sender_id:
        for s in options:
            if s['id'] == sender_id:
                return s
    return options[0]


def config(sender_id=None):
    s = resolve_sender(sender_id)
    return {
        'sender_id': s['id'],
        'sender_name': s['name'],
        'sender_title': s['title'],
        'sender_email': s['reply_to'],
        'sender_org': os.environ.get('RFP_SENDER_ORG', 'Impact Analytics'),
        'sender_phone': os.environ.get('RFP_SENDER_PHONE', ''),
        # Set when the sender keeps several Google accounts signed in and the
        # compose window opens under the wrong one.
        'gmail_account': os.environ.get('GMAIL_ACCOUNT_INDEX', ''),
    }


def build_subject(venue, night, sender_id=None):
    return (
        f"Private event enquiry — {night['date']} · "
        f"{night['headcount']} · {config(sender_id)['sender_org']}"
    )


# One generic set of asks, worded to suit a standing reception and a seated
# dinner alike.
_ASKS = [
    "Availability on the date above, and the largest hold you can place while we confirm",
    "Confirmation the space takes this many guests comfortably in this format, rather than at capacity",
    "Food and drink options you would recommend at this headcount, and the format you would advise",
    "Food & beverage minimum and/or room fee — and whether NRF week carries a premium",
    "Beverage packages, including a substantial non-alcoholic selection",
    "Whether the space is private or semi-private, and what else is running in the room that evening",
    "AV and a microphone, in case we open with a short welcome",
    "Deposit schedule, payment terms and the cancellation policy",
    "Dietary accommodation — we expect vegetarian, vegan, halal and gluten-free guests",
    "Whether service charge, administrative fee and tax are included in the figures you quote",
]


def build_body(venue, night, event, sender_id=None):
    cfg = config(sender_id)
    space = venue.get('space') or 'your private dining space'

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
    lines += [f"  {i}. {ask}" for i, ask in enumerate(_ASKS, start=1)]
    lines += [
        "",
        "We are comparing a short list of venues over the next two weeks and will "
        "move quickly once we have proposals in hand. A PDF pack or a call both work — "
        "whichever is easier for you.",
        "",
        "Thank you,",
        cfg['sender_name'],
        f"{cfg['sender_title']}, {cfg['sender_org']}" if cfg['sender_title'] else cfg['sender_org'],
    ]
    if cfg['sender_phone']:
        lines.append(cfg['sender_phone'])
    lines.append(cfg['sender_email'])
    return "\n".join(lines)


def gmail_url(venue, night, event, sender_id=None):
    """A Gmail compose URL, prefilled. Rendered into the page as a plain link so
    the click opens a tab directly and is never caught by a popup blocker."""
    cfg = config(sender_id)
    base = GMAIL_COMPOSE
    if cfg['gmail_account']:
        base = f"{GMAIL_COMPOSE}u/{cfg['gmail_account']}/"
    params = {
        'view': 'cm',
        'fs': '1',
        'to': venue.get('email', ''),
        'su': build_subject(venue, night, sender_id),
        'body': build_body(venue, night, event, sender_id),
    }
    return base + '?' + urllib.parse.urlencode(params)
