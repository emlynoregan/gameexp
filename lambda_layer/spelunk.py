from pydantic import BaseModel
from typing import Dict, Optional
from shared import project_dict, calc_spelunk_pkey, str_to_hashed_id, normalize_url
from ddb import get_item, put_item, query, delete_item, update_item
import uuid
import time
from youtube import is_youtube_url, get_youtube_data, get_youtube_transcript_url, get_youtube_summary_url
import os

# the dynamo record will have these attributes:
# pkey: string
# id: string
# version: int
# name: string
# overview: string
# type: string
# created_at: unix timestamp
# updated_at: unix timestamp
# lenses: dict of dicts
#   lens_url: string
#   lens_type: string
#   lens_status: string

C_STATUS_PREPARING = 'preparing'
C_STATUS_UNDERWAY = 'underway'
C_STATUS_READY = 'ready'
C_STATUS_ERROR = 'error'

C_CURRENT_VERSION = 1

class Lens(BaseModel):
    status: str
    # url is optional
    url: Optional[str]
    type: Optional[str]
    message: Optional[str]

    def __init__(self, **data):
        super().__init__(**data)
        self.status = data.get('status')
        self.url = data.get('url')
        self.type = data.get('type')
        self.message = data.get('message')
 
class Spelunk(BaseModel):
    id: str
    version: int
    name: str
    overview: str
    type: str
    created_at: int
    updated_at: int
    lenses: Dict[str, Lens]
 
    def __init__(self, **data):
        print (data)
        super().__init__(**data)
        self.id = data.get('id')
        self.version = data.get('version')
        self.name = data.get('name')
        self.overview = data.get('overview')
        self.type = data.get('type')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
        self.lenses = {key: Lens(**value) for key, value in data.get('lenses').items()}

def spelunk_rec_to_api(spelunk_rec):
    api_obj = {
        **project_dict(
            spelunk_rec, [
                'id',
                'version',
                'name',
                'overview',
                'type',
                'created_at',
                'updated_at',
                'lenses'
            ]
        )
    }

    return Spelunk(**api_obj)

def create_spelunk_rec_from_url(url):
    # first test if this is a youtube url
    # if so, create a spelunk record with the youtube url
    # and return the spelunk record

    if not is_youtube_url(url):
        raise Exception('Not a valid youtube url')
    
    # normalize the url
    norm_url = normalize_url(url)

    id = str_to_hashed_id(norm_url)

    # before proceeding, check if this spelunk already exists
    # if so, return the existing spelunk

    spelunk_rec = get_spelunk_rec(id)

    if spelunk_rec:
        return spelunk_rec

    table_name = os.environ['table_name']

    pkey = calc_spelunk_pkey(id)

    now = int(time.time())

    youtube_data = get_youtube_data(url)

    item = {
        'pkey': pkey,
        'id': id,
        'version': C_CURRENT_VERSION,
        'name': youtube_data['title'],
        'overview': youtube_data['title'],
        'type': 'youtube',
        'created_at': now,
        'updated_at': now,
        'lenses': {
            'source': {
                'status': C_STATUS_READY,
                'url': url,
                'type': 'youtube'
            },
            'transcript': {
                'status': C_STATUS_PREPARING,
            },
            'summary': {
                'status': C_STATUS_PREPARING,
            }
        }
    }

    put_item(table_name, item)

    return item

def create_spelunk_from_url(url, s3_bucket):
    spelunk_rec = create_spelunk_rec_from_url(url)

    spelunk_rec = add_temporary_urls_to_spelunk_rec(spelunk_rec, s3_bucket)

    return Spelunk(**spelunk_rec)

def get_spelunk_rec(spelunk_id):
    table_name = os.environ['table_name']

    pkey = calc_spelunk_pkey(spelunk_id)

    item = get_item(table_name, pkey)

    spelunk_rec = item.get('Item')

    if not spelunk_rec:
        return None
    
    return spelunk_rec

def get_spelunk_by_id(spelunk_id, s3_bucket):
    spelunk_rec = get_spelunk_rec(spelunk_id)

    if not spelunk_rec:
        return None
    
    spelunk_rec = add_temporary_urls_to_spelunk_rec(spelunk_rec, s3_bucket)

    return Spelunk(**spelunk_rec)

def spelunk_rec_needs_processing(spelunk_rec):
    return spelunk_rec_needs_transcript(spelunk_rec) or spelunk_rec_needs_summary(spelunk_rec)

def spelunk_rec_needs_transcript(spelunk_rec):
    lens = spelunk_rec['lenses']['transcript']
    
    try:
        started_at = int(lens.get('started_at')) or 0
    except:
        started_at = 0

    # we need the transcript if it's in the preparing state, or in the underway state and the started_at timestamp is more than 15 minutes ago
    return lens['status'] == C_STATUS_PREPARING or (lens['status'] == C_STATUS_UNDERWAY and started_at > 900)

def spelunk_rec_needs_summary(spelunk_rec):
    lens = spelunk_rec['lenses']['summary']

    try:
        started_at = int(lens.get('started_at')) or 0
    except:
        started_at = 0

    # we need the summary if it's in the preparing state, or in the underway state and the started_at timestamp is more than 15 minutes ago
    return lens['status'] == C_STATUS_PREPARING or (lens['status'] == C_STATUS_UNDERWAY and started_at > 900)

def update_spelunk_rec(spelunk_rec):
    # copy the spelunk record
    spelunk_rec_copy = spelunk_rec.copy()

    pkey = spelunk_rec_copy.get('pkey') or calc_spelunk_pkey(spelunk_rec_copy['id'])
    # updated = spelunk_rec.get('updated_at')
    if 'pkey' in spelunk_rec_copy:
        del spelunk_rec_copy['pkey']

    # # need a conditional update that checks the updated_at timestamp
    # condition_expression = 'updated_at = :updated_at'
    # expression_attribute_values = {':updated_at': updated}

    update_item(os.environ['table_name'], pkey=pkey, set_value=spelunk_rec_copy) #, condition_expression=condition_expression, expression_attribute_values=expression_attribute_values)

def add_temporary_urls_to_spelunk_rec(spelunk_rec, s3_bucket):
    # add temporary urls to the spelunk record
    # this is used for testing

    # if the transcript is ready, add a temporary url
    if spelunk_rec['lenses']['transcript']['status'] == C_STATUS_READY:
        spelunk_rec['lenses']['transcript']['url'] = get_youtube_transcript_url(spelunk_rec, s3_bucket)

    # if the summary is ready, add a temporary url
    if spelunk_rec['lenses']['summary']['status'] == C_STATUS_READY:
        spelunk_rec['lenses']['summary']['url'] = get_youtube_summary_url(spelunk_rec, s3_bucket)

    return spelunk_rec