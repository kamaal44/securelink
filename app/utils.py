import re
import uuid
import boto3
from flask import current_app
from datetime import datetime

def log_status_to_db(barcode, status, source):
    dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table(current_app.config["DB_TABLENAME"])
    res = table.put_item(Item={
        'id': str(uuid.uuid4()),
        'barcode': barcode,
        'result_status': status,
        'access_timestamp': str(datetime.utcnow()),
        'source': source,
    })
    return res

def validate_form_fields(barcode, dob, source):
    # check for 8 or 16 digit barcode
    if not re.match(r'^(.{8}|.{16})$', barcode):
        return False
    # validate dob
    elif not re.match(r'(\d{4})-(\d{2})-(\d{2})', dob):
        return False
    # validate study
    elif source not in ["scan", "securelink"]:
        return False
    # input OK
    else:
        return True
