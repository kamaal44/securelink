import re
import json
import boto3
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

    # todo; calculate hashed value here
    hashstr = barcode
    key = f"covid19/results/{hashstr}.json"
    obj = boto3.client('s3').get_object(Bucket=app.config["S3_BUCKET"], Key=key)
    result = json.load(obj["Body"])
    return render_template('results.html', result=result)