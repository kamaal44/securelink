import uuid
import boto3
from flask import current_app
from datetime import datetime

def log_status_to_db(barcode, status):
    dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table(current_app.config["DB_TABLENAME"])
    res = table.put_item(Item={
        'id': str(uuid.uuid4()),
        'barcode': barcode,
        'result_status': status,
        'access_timestamp': str(datetime.utcnow())
    })
    return res