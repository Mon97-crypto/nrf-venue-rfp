"""RFP composition and Gmail hand-off.

One generic RFP body, deliberately free of any conference name or date: it
describes the shape of the evening — format, headcount, timing, space — and
asks the venue what they can do. Whoever sends it adds the date in Gmail, or
settles it in the reply.

The body carries no sign-off block either, so Gmail's own signature is the only
one on the message.
"""
import json
import os
import urllib.parse

GMAIL_COMPOSE = 'https://mail.google.com/mail/'
_SENDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'senders.json')


def sending_account():
    """The Google account the compose window should open under."""
    env = os.environ.get('GMAIL_SENDING_ACCOUNT', '')
    if env:
        return env
    try:
        with open(_SENDERS_FILE, 'r', encoding='utf-8') as fh:
            return json.load(fh).get('sending_account', '') or ''
    except (OSError, ValueError):
        return ''


def config():
    return {
        'sending_account': sending_account(),
        'sender_org': os.environ.get('RFP_SENDER_ORG', 'Impact Analytics'),
    }


def build_subject(venue, night):
    return f"Private event enquiry — {night['headcount']} · {config()['sender_org']}"


# One generic set of asks, worded to suit a standing reception and a seated
# dinner alike. No date is quoted anywhere, so availability is the opening ask.
_ASKS = [
    "Your availability, and how far ahead you take bookings of this size",
    "Confirmation the space takes this many guests comfortably in this format, rather than at capacity",
    "Food and drink options you would recommend at this headcount, and the format you would advise",
    "Food & beverage minimum and/or room fee, and how that varies by day of the week",
    "Beverage packages, including a substantial non-alcoholic selection",
    "Whether the space is private or semi-private, and what else would be running in the room",
    "AV and a microphone, in case we open with a short welcome",
    "Deposit schedule, payment terms and the cancellation policy",
    "Dietary accommodation — we expect vegetarian, vegan, halal and gluten-free guests",
    "Whether service charge, administrative fee and tax are included in the figures you quote",
]


def build_body(venue, night, event=None):
    cfg = config()
    space = venue.get('space') or 'your private dining space'

    lines = [
        f"Hello {venue['name']} events team,",
        "",
        f"I'm writing from {cfg['sender_org']} about a private event we are "
        f"planning in New York.",
        "",
        f"  Event      {night['format']}",
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
        "I'm happy to share exact dates once we know what you have available. "
        "A PDF pack or a call both work — whichever is easier for you.",
        "",
        "Thank you,",
    ]
    return "\n".join(lines)


def gmail_url(venue, night, event=None):
    """A Gmail compose URL, prefilled. Rendered into the page as a plain link so
    the click opens a tab directly and is never caught by a popup blocker."""
    params = {
        'view': 'cm',
        'fs': '1',
        'to': venue.get('email', ''),
        'su': build_subject(venue, night),
        'body': build_body(venue, night),
    }
    # Ask Google to open the compose window under the sending account, for
    # people signed into several at once.
    account = sending_account()
    if account:
        params['authuser'] = account
    return GMAIL_COMPOSE + '?' + urllib.parse.urlencode(params)
