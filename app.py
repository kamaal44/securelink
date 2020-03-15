import re
import json
import boto3
from datetime import datetime
from flask import Flask, request, render_template, redirect
app = Flask(__name__)

app.config["S3_BUCKET"] = "dokku-stack-phi"

@app.route('/')
def home():
    # serve homepage
    barcode = request.args.get('code', "")
    return render_template('index.html', barcode=barcode)


@app.route('/result', methods=['POST'])
def show_result():
    barcode = request.form['barcode']
    dob = request.form['dob']

    if not re.match(r'(.{4})-(.{4})-(.{4})-(.{4})', barcode):
        return redirect("/")

    if not re.match(r'(\d{2})/(\d{2})/(\d{4})', dob):
        return redirect("/")
    
    try:
        dobdt = datetime.strptime(dob, "%m/%d/%Y")    
        dobstr = dobdt.strftime('%Y-%m-%d')
        barcode = barcode.replace("-", "")
    except:
        return redirect('/error')

    key = f"covid19/results/{barcode}-{dobstr}.json"
    
    try:
        obj = boto3.client('s3').get_object(Bucket=app.config["S3_BUCKET"], Key=key)
    except:
        return redirect('/error')
    result = json.load(obj["Body"])
    print(f"{key} retrieved; status is {result['status_code']}")
    return render_template('results.html', result=result)

@app.route('/error')
def error():
    return render_template('error.html')
