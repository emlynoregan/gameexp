# the dynamo record will have these attributes:
# pkey: string
# l2_pkey: string
# l2_skey: string
# plugin_id: string
# plugin_name: string
# plugin_url: string
# roles: dict of list of strings
# disabled: boolean
# owner_user_id: string
# created: unix timestamp
# updated: unix timestamp

# import BaseModel
from pydantic import BaseModel

from shared import project_dict, calc_plugin_pkey, calc_plugin_l2_pkey, calc_plugin_l2_skey
from user import get_user_rec
from ddb import get_item, put_item, query, delete_item, update_item
import os
import uuid
import time
import typing

# types for FastAPI.

class Plugin(BaseModel):
    plugin_id: str
    plugin_name: str
    plugin_url: str
    roles: dict[str, list[str]]
    disabled: bool
    owner_user_id: str
    created: int
    updated: int

    def __init__(self, **data):
        super().__init__(**data)
        self.plugin_id = data.get('plugin_id')
        self.plugin_name = data.get('plugin_name')
        self.plugin_url = data.get('plugin_url')
        self.roles = data.get('roles')
        self.disabled = data.get('disabled')
        self.owner_user_id = data.get('owner_user_id')
        self.created = data.get('created')
        self.updated = data.get('updated')

class PluginList(BaseModel):
    plugins: list[Plugin]
    # cursor can be a string or None
    cursor: typing.Optional[str]

    def __init__(self, **data):
        super().__init__(**data)
        self.plugins = data.get('plugins')
        self.cursor = data.get('cursor')

class DeletedPlugin(BaseModel):
    plugin_id: str
    deleted: bool = True

    def __init__(self, **data):
        super().__init__(**data)
        self.plugin_id = data.get('plugin_id')


def plugin_rec_to_api(plugin_rec) -> Plugin:
    api_obj = {
        **project_dict(
            plugin_rec,
            [
                'plugin_id',
                'plugin_name',
                'plugin_url',
                'roles',
                'disabled',
                'owner_user_id',
                'created',
                'updated'
            ]
        )
    }

    return Plugin(**api_obj)

def to_plugin_list(plugin_recs, cursor) -> PluginList:
    plugins = [plugin_rec_to_api(plugin_rec) if isinstance(plugin_rec, dict) else plugin_rec 
                for plugin_rec in plugin_recs]

    return PluginList(plugins=plugins, cursor=cursor)

def to_deleted_plugin(plugin_id) -> DeletedPlugin:
    return DeletedPlugin(plugin_id=plugin_id)

def create_plugin_rec(owner_user_id, plugin_name, plugin_url, roles=None):
    # user_rec = get_user_rec(owner_user_id) # likely throws an exception if user not found

    # if not user_rec:
    #     raise Exception('user not found')

    table_name = os.environ['table_name']

    plugin_id = str(uuid.uuid4())

    pkey = calc_plugin_pkey(plugin_id)
    l2_pkey = calc_plugin_l2_pkey(owner_user_id)
    l2_skey = calc_plugin_l2_skey(plugin_name, plugin_id)

    created = int(time.time())

    item = {
        'pkey': pkey,
        'l2_pkey': l2_pkey,
        'l2_skey': l2_skey,
        'plugin_id': plugin_id,
        'plugin_name': plugin_name,
        'plugin_url': plugin_url,
        'roles': roles,
        'disabled': False,
        'owner_user_id': owner_user_id,
        'created': created,
        'updated': created
    }

    put_item(
        table_name,
        item
    )

    return item

def get_plugin_rec(plugin_id):
    table_name = os.environ['table_name']

    pkey = calc_plugin_pkey(plugin_id)

    item = get_item(
        table_name,
        pkey
    )

    return item.get('Item')

def list_plugin_recs_by_owner_user_id(owner_user_id, cursor = None, limit = 100):
    table_name = os.environ['table_name']

    l2_pkey = calc_plugin_l2_pkey(owner_user_id)

    result = query(
        table_name,
        l2_pkey,
        pkey_name='l2_pkey',
        index_name = 'lookup2',
        limit = limit,
        cursor = cursor
    )

    new_cursor = result.get('Cursor')

    return new_cursor, result.get('Items') or []

def update_plugin_rec(plugin_id, plugin):
    table_name = os.environ['table_name']

    pkey = calc_plugin_pkey(plugin_id)

    # you can only update the plugin_name, plugin_url, roles, and disabled fields

    updated = int(time.time())

    response = update_item(
        table_name,
        pkey,
        set_value = {
            'plugin_name': plugin.plugin_name,
            'plugin_url': plugin.plugin_url,
            'roles': plugin.roles,
            'disabled': plugin.disabled,
            'updated': updated
        }
    )

    item = response['Attributes']

    return item

def delete_plugin_rec(plugin_id):
    # hard delete
    table_name = os.environ['table_name']

    pkey = calc_plugin_pkey(plugin_id)

    delete_item(
        table_name,
        pkey
    )
