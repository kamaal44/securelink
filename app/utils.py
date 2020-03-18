import boto3
from flask import current_app
from datetime import datetime



def log_status_to_db(barcode, status):
    dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table(current_app.config["DB_TABLENAME"])
    res = table.update_item(
        Key={
            'barcode': barcode
        },
        UpdateExpression="set last_status = :r, last_timestamp = :t",
        ExpressionAttributeValues={
            ':r': status,
            ':t': str(datetime.utcnow())
        },
        ReturnValues="UPDATED_NEW"
    )
    return res