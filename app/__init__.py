import re
import json
import boto3
import logging
from datetime import datetime
from flask import Flask, request, render_template, redirect, Response, abort
from flask_limiter import Limiter
from flask_limiter.util import get_ipaddr
from flask_talisman import Talisman
from pathlib import Path
from botocore.exceptions import ClientError

from .utils import log_status_to_db, validate_form_fields

app = Flask(__name__)

# flask-talisman adds additional best-practice security considerations
# note that force_https is off because of our proxy
Talisman(app, content_security_policy=None, force_https=False)

app.config["S3_BUCKET"] = "dokku-stack-phi"
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

base = Path(__file__).resolve().parent.parent

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
        source = "securelink"
        dobdt = datetime.strptime(dob, "%m/%d/%Y")
        dobstr = dobdt.strftime('%Y-%m-%d')
    except:
        return redirect('/error')

    if not validate_form_fields(barcode, dobstr, source):
        return redirect("/error")

    key = f"covid19/results/{barcode}-{dobstr}.json"

    try:
        obj = boto3.client('s3').get_object(Bucket=app.config["S3_BUCKET"], Key=key)
    except:
        return redirect('/error')
    result = json.load(obj["Body"])

    # status logging
    app.logger.info(f"{key} retrieved; status is {result['status_code']}")
    log_status_to_db(barcode, result['status_code'], source)

    return render_template('results.html', result=result)


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
        obj = boto3.client('s3').get_object(Bucket=app.config["S3_BUCKET"], Key=key)
        result = json.load(obj["Body"])
        # status logging
        app.logger.info(f"{key} retrieved; status is {result['status_code']}")
        log_status_to_db(barcode, result['status_code'], source)

    except ClientError:
        try:
            filepath = f"test_results/scan/{barcode}-{dobstr}.json"

            with open(base / filepath, 'r') as json_file:
                result = json.load(json_file)

            app.logger.info(f"{key} retrieved; status is {result['status_code']}")

        except:
            return redirect('/scan/error')

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
    source = "scan"

    if not validate_form_fields(barcode, dob, source):
        return abort(404)

    key = f"covid19/results-scan-study/{barcode}-{dob}.pdf"

    try:
        res = boto3.client('s3').get_object(Bucket=app.config['S3_BUCKET'], Key=key)
        return Response(res['Body'].read(),
            mimetype='application/pdf',
            headers={"Content-Disposition": f"attachment;filename={barcode}-{dob}.pdf"})
    except ClientError:
        try:
            filepath = base / f"reports/{barcode}-{dob}.pdf"
            with open(filepath, 'rb') as pdf_file:
                res = pdf_file.read()

            return Response(res,
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment;filename={barcode}-{dob}.pdf'})

        except:
            return abort(404)
