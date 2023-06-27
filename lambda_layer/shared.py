import re
import os 
import json
import base64
from fastapi import HTTPException
import boto3

# dynamodb_client.create_table(
#     TableName=TableName,
#     KeySchema=[
#         {
#             'AttributeName': 'pkey',
#             'KeyType': 'HASH'
#         }
#     ],
#     GlobalSecondaryIndexes=[
#         {
#             'IndexName': 'lookup1',
#             'KeySchema': [
#                 {
#                     'AttributeName': 'l1_pkey',
#                     'KeyType': 'HASH'
#                 },
#                 {
#                     'AttributeName': 'l1_skey',
#                     'KeyType': 'RANGE'
#                 }
#             ],
#             'Projection': {
#                 'ProjectionType': 'ALL'
#             },
#         },
#         {
#             'IndexName': 'lookup2',
#             'KeySchema': [
#                 {
#                     'AttributeName': 'l2_pkey',
#                     'KeyType': 'HASH'
#                 },
#                 {
#                     'AttributeName': 'l2_skey',
#                     'KeyType': 'RANGE'
#                 }
#             ]
#         },
#         {
#             'IndexName': 'lookup3',
#             'KeySchema': [
#                 {
#                     'AttributeName': 'l3_pkey',
#                     'KeyType': 'HASH'
#                 },
#                 {
#                     'AttributeName': 'l3_skey',
#                     'KeyType': 'RANGE'
#                 }
#             ]
#         },
#         {
#             'IndexName': 'lookup4',
#             'KeySchema': [
#                 {
#                     'AttributeName': 'l4_pkey',
#                     'KeyType': 'HASH'
#                 },
#                 {
#                     'AttributeName': 'l4_skey',
#                     'KeyType': 'RANGE'
#                 }
#             ]
#         }
#     ],
#     AttributeDefinitions=[
#         {
#             'AttributeName': 'pkey',
#             'AttributeType': 'S'
#         },
#         {
#             'AttributeName': 'l1_pkey',
#             'AttributeType': 'S'
#         },
#         {
#             'AttributeName': 'l1_skey',
#             'AttributeType': 'S'
#         },
#         {
#             'AttributeName': 'l2_pkey',
#             'AttributeType': 'S'
#         },
#         {
#             'AttributeName': 'l2_skey',
#             'AttributeType': 'S'
#         },
#         {
#             'AttributeName': 'l3_pkey',
#             'AttributeType': 'S'
#         },
#         {
#             'AttributeName': 'l3_skey',
#             'AttributeType': 'S'
#         },
#         {
#             'AttributeName': 'l4_pkey',
#             'AttributeType': 'S'
#         },
#         {
#             'AttributeName': 'l4_skey',
#             'AttributeType': 'S'
#         }
#     ],
#     BillingMode='PAY_PER_REQUEST'
# )

# the ttl attribute is called 'ttl'

C_DOMAIN_NAME = os.environ['domain_name']

C_ACCESSTOKEN = "AT"

C_USER = "U"
C_SPELUNK = "S"

def safe_id(id):
    # only allow alphanumeric characters and underscores
    # replace all other characters with underscores
    return re.sub(r'[^a-zA-Z0-9_]', '_', id)

# Q: What's the best way to calculate a sha1 hash in Python?
# A: hashlib.sha1()
import hashlib
def str_to_hashed_id(s):
    # use a crytographic hash here
    s_sha1 = hashlib.sha1(s.encode('utf-8')).hexdigest()
    return s_sha1

def normalize_url(url):
    # remove trailing slash
    url = url.rstrip('/')
    # remove http://
    url = url.replace('http://', '')
    # remove https://
    url = url.replace('https://', '')
    # remove www.
    url = url.replace('www.', '')
    # convert to lowercase
    # this is invalid for some urls, but it's good enough for our purposes
    url = url.lower()
    return url

# def calc_access_token_pkey(access_token_id):
#     return f"{C_ACCESSTOKEN}*{safe_id(access_token_id)}"

# def calc_access_token_l1_pkey(access_token):
#     return f"{C_ACCESSTOKEN}*{safe_id(access_token)}"

# def calc_access_token_l1_skey():
#     return "-"

# def calc_user_pkey(user_id):
#     return f"{C_USER}*{safe_id(user_id)}"

# def calc_user_l1_pkey(external_id):
#     return f"{C_USER}*{safe_id(external_id)}"

# def calc_user_l1_skey():
#     return "-"

def calc_spelunk_pkey(spelunk_id):
    return f"{C_SPELUNK}*{safe_id(spelunk_id)}"

# the following function is a decorator that caches the result of the function
# in a global dictionary.
# the function is decorated with @cache_result

CACHE = {} 

def cache_result(func):
    def wrapper(*args, **kwargs):
        key = (func.__name__, args, frozenset(kwargs.items()))
        if key not in CACHE:
            CACHE[key] = func(*args, **kwargs)
        return CACHE[key]
    return wrapper

import traceback
def exc_to_string(exc):
    return ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))

def project_dict(d, keys):
    return {k: v for k, v in d.items() if k in keys}

def flatten_for_api(d):
    return {
        k: json.dumps(v) if isinstance(v, (dict, list, set, tuple)) else v
        for k, v in d.items()
    }

def remove_none_attribs(d):
    return {k: v for k, v in d.items() if v is not None}

def process_op_in_blambda(group_id, op, detail_dict):
    print (f"process_op_in_blambda: {group_id}, {op}, {detail_dict}")
    queue_url = os.environ['queue_url']

    sqs = boto3.client('sqs')

    _ = sqs.send_message(
        QueueUrl=queue_url,
        MessageGroupId=group_id,
        MessageBody=json.dumps({
            "op": op,
            "detail": detail_dict
        })
    )
