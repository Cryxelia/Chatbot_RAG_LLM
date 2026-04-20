import os
import sys
import traceback
from datetime import datetime
from django.core.wsgi import get_wsgi_application

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'project'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

try:
    application = get_wsgi_application()
except Exception:
    log_file = os.path.join(BASE_DIR, 'wsgi_error.log')
    with open(log_file, 'w') as f: 
        f.write(f"WSGI startup error: {datetime.now().isoformat()}\n")
        f.write(traceback.format_exc())    

    def application(environ, start_response):
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [b'WSGI startup error, se wsgi_error.log']
