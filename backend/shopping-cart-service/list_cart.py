import json
import os

import boto3
from boto3.dynamodb.conditions import Key

from shared import get_cart_id, get_headers, get_user_sub, handle_decimal_type


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def lambda_handler(event, context):
    """
    List items in shopping cart.
    """

    cart_id, generated = get_cart_id(event["headers"])

    # Because this method can be called anonymously, we need to check there's a logged in user
    jwt_token = event["headers"].get("Authorization")
    if jwt_token:
        user_sub = get_user_sub(jwt_token)
        key_string = f"user#{user_sub}"
    else:
        key_string = f"cart#{cart_id}"

    # No need to query database if the cart_id was generated rather than passed into the function
    if generated:
        product_list = []
    else:
        response = table.query(
            KeyConditionExpression=Key("pk").eq(key_string)
            & Key("sk").begins_with("product#"),
            ProjectionExpression="sk,quantity,productDetail",
            FilterExpression="quantity > :val",  # Only return items with more than 0 quantity
            ExpressionAttributeValues={":val": 0},
        )
        product_list = response.get("Items", [])

    for product in product_list:
        product.update(
            (k, v.replace("product#", "")) for k, v in product.items() if k == "sk"
        )

    return {
        "statusCode": 200,
        "headers": get_headers(cart_id),
        "body": json.dumps({"products": product_list}, default=handle_decimal_type),
    }
