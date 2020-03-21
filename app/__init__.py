import re
import json
import boto3
import logging
from datetime import datetime
from flask import Flask, request, render_template, redirect, Response, abort
from flask_limiter import Limiter
from flask_limiter.util import get_ipaddr
from flask_talisman import Talisman

from .utils import log_status_to_db, validate_form_fields

app = Flask(__name__)

# flask-talisman adds additional best-practice security considerations
# note that force_https is off because of our proxy
Talisman(app, content_security_policy=None, force_https=False)

app.config["S3_BUCKET"] = "dokku-stack-phi"
app.config["DB_TABLENAME"] = "securelink.event_log"

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
    return render_template('index.html', barcode=barcode)

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
        source = request.form['source']
        dobdt = datetime.strptime(dob, "%m/%d/%Y")
        dobstr = dobdt.strftime('%Y-%m-%d')
    except:
        return redirect('/error')

    if not validate_form_fields(barcode, dobstr, source):
        return redirect("/error")

    if source == "scan":
        key = f"covid19/results-scan-study/{barcode}-{dobstr}.json"
    else:
        key = f"covid19/results/{barcode}-{dobstr}.json"
    try:
        obj = boto3.client('s3').get_object(Bucket=app.config["S3_BUCKET"], Key=key)
    except:
        return redirect('/error')
    result = json.load(obj["Body"])

    # status logging
    app.logger.info(f"{key} retrieved; status is {result['status_code']}")
    log_status_to_db(barcode, result['status_code'], source)

    if source == "scan":
        return render_template('scan/results.html', result=result)
    else:
        return render_template('results.html', result=result)


@app.route('/error')
def error():
    return render_template('error.html')


@app.route('/pdfreport', methods=['POST'])
def get_pdf_report():
    barcode = request.form['barcode']
    dob = request.form['dob']
    source = request.form['source']

    if not validate_form_fields(barcode, dob, source):
        return abort(404)

    key = f"covid19/results-scan-study/{barcode}-{dob}.pdf"

    try:
        res = boto3.client('s3').get_object(Bucket=app.config['S3_BUCKET'], Key=key)
    except:
        return abort(404)

    return Response(res['Body'].read(),
        mimetype='application/pdf',
        headers={"Content-Disposition": f"attachment;filename={barcode}-{dob}.pdf"})
