"""Flask blueprint for the NRF venue RFP tool, mounted at /venues."""
import json
import os
import re

from flask import Blueprint, jsonify, render_template, request, Response

from . import covers, mailer, store

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, 'data', 'venues.json')

venue_bp = Blueprint(
    'venues',
    __name__,
    url_prefix='/venues',
    template_folder=os.path.join(_HERE, 'templates'),
)


def load_catalog():
    with open(_DATA, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def _monogram(name):
    """Initials used on the generated cover when no image is set."""
    words = [w for w in re.split(r'[^A-Za-z]+', name) if w]
    letters = ''.join(w[0] for w in words)[:2] or name[:2]
    return letters.upper()


def _decorate(catalog, with_links=False):
    """Merge stored outreach state and per-venue overrides onto the catalog."""
    outreach = store.all_outreach()
    meta = store.all_meta()
    venues = []
    for v in catalog['venues']:
        v = dict(v)
        m = meta.get(v['id'], {})
        v['cover_image'] = m.get('cover_image', '') or v.get('cover_image', '')
        override = m.get('email_override', '')
        if override:
            v['email'] = override
            v['email_confidence'] = 'user_supplied'
        v['monogram'] = _monogram(v['name'])
        if with_links:
            # Rendered into the page as a real href so the click opens Gmail
            # directly, rather than through JS a popup blocker might catch.
            v['gmail'] = {
                night: mailer.gmail_url(v, cfg, catalog['event'])
                for night, cfg in catalog['event']['nights'].items()
            }
        v['outreach'] = {
            night: outreach.get(v['id'], {}).get(night, {'status': 'not_contacted', 'notes': ''})
            for night in catalog['event']['nights']
        }
        venues.append(v)
    venues.sort(key=lambda x: x.get('proximity_rank', 99))
    return venues


@venue_bp.route('/')
def index():
    catalog = load_catalog()
    return render_template(
        'venues.html',
        event=catalog['event'],
        venues=_decorate(catalog, with_links=True),
        statuses=store.STATUSES,
        status_labels=store.STATUS_LABELS,
        mail_config=mailer.config(),
    )


@venue_bp.route('/api/venues')
def api_venues():
    catalog = load_catalog()
    return jsonify({'event': catalog['event'], 'venues': _decorate(catalog)})


@venue_bp.route('/api/draft/<venue_id>/<night_id>')
def api_draft(venue_id, night_id):
    catalog = load_catalog()
    venue = next((v for v in _decorate(catalog) if v['id'] == venue_id), None)
    night = catalog['event']['nights'].get(night_id)
    if not venue or not night:
        return jsonify({'error': 'Unknown venue or night.'}), 404
    return jsonify({
        'to': venue.get('email', ''),
        'subject': mailer.build_subject(venue, night),
        'body': mailer.build_body(venue, night, catalog['event']),
        'gmail_url': mailer.gmail_url(venue, night, catalog['event']),
        'email_confidence': venue.get('email_confidence', 'unconfirmed'),
        'booking_note': venue.get('booking_note', ''),
    })


@venue_bp.route('/api/outreach/<venue_id>/<night_id>', methods=['POST'])
def api_outreach(venue_id, night_id):
    payload = request.get_json(silent=True) or {}
    try:
        row = store.upsert_outreach(
            venue_id, night_id,
            status=payload.get('status'),
            notes=payload.get('notes'),
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(row)


@venue_bp.route('/api/meta/<venue_id>', methods=['POST'])
def api_meta(venue_id):
    payload = request.get_json(silent=True) or {}
    row = store.upsert_meta(
        venue_id,
        cover_image=payload.get('cover_image'),
        email_override=payload.get('email_override'),
    )
    return jsonify(row)


@venue_bp.route('/api/cover/<venue_id>', methods=['POST'])
def api_cover(venue_id):
    """Pull this venue's own hero image off its own website and store it."""
    catalog = load_catalog()
    venue = next((v for v in catalog['venues'] if v['id'] == venue_id), None)
    if not venue:
        return jsonify({'error': 'Unknown venue.'}), 404
    try:
        url = covers.fetch_cover(venue.get('website', ''))
    except covers.CoverError as exc:
        return jsonify({'error': str(exc), 'venue': venue['name']}), 502
    store.upsert_meta(venue_id, cover_image=url)
    return jsonify({'ok': True, 'venue': venue['name'], 'cover_image': url})


@venue_bp.route('/api/covers', methods=['POST'])
def api_covers():
    """Fetch every missing cover in one pass, reporting per venue."""
    catalog = load_catalog()
    force = bool((request.get_json(silent=True) or {}).get('force'))
    have = store.all_meta()
    results = []
    for v in catalog['venues']:
        if not force and have.get(v['id'], {}).get('cover_image'):
            results.append({'id': v['id'], 'name': v['name'], 'status': 'kept'})
            continue
        try:
            url = covers.fetch_cover(v.get('website', ''))
        except covers.CoverError as exc:
            results.append({'id': v['id'], 'name': v['name'], 'status': 'failed',
                            'error': str(exc)})
            continue
        store.upsert_meta(v['id'], cover_image=url)
        results.append({'id': v['id'], 'name': v['name'], 'status': 'fetched',
                        'cover_image': url})
    return jsonify({
        'fetched': sum(1 for r in results if r['status'] == 'fetched'),
        'failed': sum(1 for r in results if r['status'] == 'failed'),
        'kept': sum(1 for r in results if r['status'] == 'kept'),
        'results': results,
    })


@venue_bp.route('/api/export')
def api_export():
    return Response(
        store.export_json(),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=nrf2027-venue-outreach.json'},
    )
