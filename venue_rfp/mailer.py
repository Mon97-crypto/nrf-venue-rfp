"""RFP composition and Gmail hand-off.

One generic RFP body. It names no conference, but it does carry the date and
the running order, because availability and a quoted minimum are the two things
the reply has to contain and neither can be answered without them.

The body carries no sign-off block either, so Gmail's own signature is the only
one on the message.
"""
import json
import os
import urllib.parse

GMAIL_COMPOSE = 'https://mail.google.com/mail/'
_SENDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'senders.json')


def _senders():
    try:
        with open(_SENDERS_FILE, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def sending_account():
    """The Google account the compose window should open under."""
    return os.environ.get('GMAIL_SENDING_ACCOUNT', '') or _senders().get('sending_account', '')


def config():
    f = _senders()
    return {
        'sending_account': sending_account(),
        'sender_name': os.environ.get('RFP_SENDER_NAME', '') or f.get('sender_name', ''),
        'sender_org': os.environ.get('RFP_SENDER_ORG', '') or f.get('sender_org', 'Impact Analytics'),
    }


def build_subject(venue, night):
    return (f"Private event enquiry — {night['date']} · "
            f"{night['headcount']} · {config()['sender_org']}")


# One generic set of asks, worded to suit a standing reception and a seated
# dinner alike. No date is quoted anywhere, so availability is the opening ask.
def _asks(night):
    """The asks, in the order they are wanted. The capacity question uses
    'holds' for a standing reception and 'seats' for a dinner."""
    verb = night.get('capacity_verb', 'holds')
    return [
        "Availability on the date and times above",
        "Which room you'd put us in, whether it's fully private, and what else "
        "would be running alongside it",
        f"Confirmation that the space {verb} this many guests comfortably in "
        "this format, not at capacity",
        "The food & beverage minimum for that space on that date",
        "Food and drink formats you'd recommend at this headcount",
        "Beverage packages, including a substantial non-alcoholic selection",
        "Dietary accommodation — expect vegetarian, vegan, halal, and gluten-free guests",
        "All other charges — room/facility fee, service charge, administrative fee, "
        "tax, staffing, coat check, AV, overtime — so we can compare venues on a "
        "genuine all-in figure",
        "Deposit schedule, payment terms, and cancellation policy",
    ]


def build_body(venue, night, event=None):
    cfg = config()
    space = venue.get('space') or 'your private dining space'

    lines = [
        f"Hello {venue['name']} events team,",
        "",
        f"I'm writing from {cfg['sender_org']} about a private event we're "
        f"planning in New York:",
        "",
        f"* Event: {night['format']}",
        f"* Date: {night['date']}",
        f"* Guests: {night.get('count') or night['headcount']}",
        f"* Timing: {night['window']}",
        f"* Space: {space}",
        f"* Group: {night.get('group_label') or night['audience']}",
        "",
        "Could you please get back to me on the following?",
        "",
    ]
    lines += [f"{i}. {ask}" for i, ask in enumerate(_asks(night), start=1)]
    lines += [
        "",
        "If that date is already committed, I'd still welcome the minimum and fee "
        "structure — we have some flexibility. A PDF pack or a call both work, "
        "whichever is easier for you.",
        "",
        "Best regards,",
    ]
    if cfg['sender_name']:
        lines.append(cfg['sender_name'])
    lines.append(cfg['sender_org'])
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
