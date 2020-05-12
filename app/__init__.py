import re
import json
import boto3
import logging
from datetime import datetime
from flask import Flask, request, render_template, redirect, Response, abort, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_ipaddr
from flask_talisman import Talisman
from pathlib import Path
from botocore.exceptions import ClientError

from .utils import log_status_to_db, validate_form_fields

app = Flask(__name__)

DEVELOPMENT = app.env == "development"

# flask-talisman adds additional best-practice security considerations
# note that force_https is off because of our proxy
Talisman(app, content_security_policy=None, force_https=False)

S3_BUCKET = boto3.resource("s3").Bucket("dokku-stack-phi")
LOCAL_DATA = Path(__file__).resolve().parent.parent / "test_results"

app.config["DB_TABLENAME"] = {
    "securelink": "securelink.event_log",
    "scan": "scan.event_log"
}

# set up rate limiting
limiter = Limiter(
    app,
    key_func=get_ipaddr,
    default_limits=["100 per hour"]
)


gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

@app.route('/')
def home():
    # serve homepage
    barcode = request.args.get('code', "")
    dob = request.args.get('dob', "")
    return render_template('index.html', barcode=barcode, dob=dob)

@app.route('/scan')
def scan_home():
    # serve scan homepage
    barcode = request.args.get('code', "")
    return render_template('scan/index.html', barcode=barcode)

@app.route('/result', methods=['POST'])
def show_result():
    try:
        barcode = request.form['barcode'].replace("-", "").upper()
        dob = request.form['dob']
        source = "securelink"
        dobdt = datetime.strptime(dob, "%m/%d/%Y")
        dobstr = dobdt.strftime('%Y-%m-%d')
    except:
        return redirect('/error')

    if not validate_form_fields(barcode, dobstr, source):
        return redirect("/error")

    key = f"covid19/results/{barcode}-{dobstr}.json"

    try:
        result = json.load(fetch_data(key))
    except:
        return redirect('/error')

    # status logging
    app.logger.info(f"{key} retrieved; status is {result['status_code']}")

    if not DEVELOPMENT:
        log_status_to_db(barcode, result['status_code'], source)

    return render_template('results.html', result=result)


@app.route('/result_dev', methods=['GET'])
def show_result_dev():

    if not DEVELOPMENT:
        return redirect('/')

    barcode = 'FFFFFFFFFFFFFFF7'
    dob = '01/01/2020'
    source = "securelink"
    dobdt = datetime.strptime(dob, "%m/%d/%Y")
    dobstr = dobdt.strftime('%Y-%m-%d')

    result = {
        'birth_date': '2020-01-01',
        'cap_method': request.args.get('cap_method', 'LT7500'),
        'collect_ts': '2020-03-12 01:23:00',
        'pat_name': 'John Doe',
        'pat_num': 'U1111111',
        'qrcode': 'FFFFFFFFFFFFFFF7',
        'result_translation': 'Detected',
        'result_ts': '2020-03-14 14:32:00',
        'result_value': 'DET',
        'spot': 'EVSPS',
        'status': 'Positive: SARS-CoV-2 (COVID-19) Virus detected',
        'status_code': request.args.get('status_code', 'DET'),
    }

    return render_template('results.html', result=result, devmode=True)


@app.route('/scan/result', methods=['POST'])
def scan_show_result():
    try:
        barcode = request.form['barcode'].upper()
        dob = request.form['dob']
        source = "scan"
        dobdt = datetime.strptime(dob, "%m/%d/%Y")
        dobstr = dobdt.strftime('%Y-%m-%d')
    except:
        return redirect('/scan/error')

    if not validate_form_fields(barcode, dobstr, source):
        return redirect("/scan/error")

    key = f"covid19/results-scan-study/{barcode}-{dobstr}.json"

    try:
        result = json.load(fetch_data(key))
    except:
        return redirect('/scan/error')

    # status logging
    app.logger.info(f"{key} retrieved; status is {result['status_code']}")

    if not DEVELOPMENT:
        log_status_to_db(barcode, result['status_code'], source)

    return render_template('scan/results.html', result=result)

@app.route('/error')
def error():
    return render_template('error.html')

@app.route('/scan/error')
def scan_error():
    return render_template('scan/error.html')

@app.route('/scan/pdfreport', methods=['POST'])
def get_pdf_report():
    barcode = request.form['barcode']
    dob = request.form['dob']
    lang = request.form['lang']
    source = "scan"

    if not validate_form_fields(barcode, dob, source):
        return abort(404)

    if not lang in {"en", "es", "vi", "zh-Hans", "zh-Hant"}:
        return abort(404)

    filename = f"{barcode}-{dob}-{lang}.pdf"

    try:
        content = fetch_data(f"covid19/results-scan-study/{filename}")
    except:
        return abort(404)

    return Response(content,
        mimetype='application/pdf',
        headers={"Content-Disposition": f"attachment;filename={filename}"})

def fetch_data(key):
    """
    Fetch object *key* from the application's S3 bucket and return a readable
    file.

    If there's an error fetching from S3 (e.g. no credentials or key not
    found), then **in development-mode only**, the object will be loaded from
    the ``test_results/`` directory in the application root.
    """
    try:
        return S3_BUCKET.Object(key).get()["Body"]
    except ClientError:
        if DEVELOPMENT:
            assert ".." not in key
            return open(LOCAL_DATA / key, "rb")
        else:
            raise
