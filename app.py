"""NRF 2027 venue RFP tool.

Standalone Flask entrypoint. The tool itself lives in the `venue_rfp` package
as a blueprint, registered here at the site root.
"""
import os

from flask import Flask

from venue_rfp import venue_bp
from venue_rfp import store

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

store.init_db()

# The blueprint declares /venues so it can be sub-mounted on another app;
# here it is the whole application, so it takes the root.
app.register_blueprint(venue_bp, url_prefix='')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
