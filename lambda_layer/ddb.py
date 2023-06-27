'''
This file includes functions to standardize interacting with dynamodb.
'''
from cgi import print_directory
from curses import keyname
import boto3
import json
import base64

def remove_ddb_format(ddb_obj, this_is_metadata=False):
    '''
    An object in ddb_format includes metadata about the object.
    This function removes that metadata.
    '''

    if not isinstance(ddb_obj, dict) and this_is_metadata:
        raise ValueError(f'Expected ddb_obj to be a metadata dict, got {type(ddb_obj)}')

    if isinstance(ddb_obj, dict):
        def convert_ddb_num(strval):
            try:
                return int(strval)
            except ValueError:
                return float(strval)

        if this_is_metadata:
            # there should be a single key in the dict
            # the key tells us the type of the underlying value
            # the value is the actual value we want to return, but 
            # we may have to modify its type

            # check there is only one key
            if len(ddb_obj) != 1:
                # bad format
                raise ValueError(f'Bad format for metadata: {ddb_obj}')

            # get the key
            key = list(ddb_obj.keys())[0]

            if key == 'S':
                # string
                return ddb_obj[key]
            elif key == 'N':
                # number
                return convert_ddb_num(ddb_obj[key])
            elif key == 'B':
                # binary
                return ddb_obj[key]
            elif key == 'BOOL':
                # boolean
                return ddb_obj[key]
            elif key == 'NULL':
                # null
                return None
            elif key == 'M':
                # map
                return remove_ddb_format(ddb_obj[key], this_is_metadata=False)
            elif key == 'L':
                # list
                return remove_ddb_format(ddb_obj[key], this_is_metadata=False)
            elif key == 'SS':
                # set of strings
                return set(ddb_obj[key])
            elif key == 'NS':
                # set of numbers
                return set([convert_ddb_num(x) for x in ddb_obj[key]])
            elif key == 'BS':
                # set of binaries
                return set(ddb_obj[key])
            else:
                # bad format
                raise ValueError(f'Unknown key in ddb metadata: {key}')
        else:
            # this is not metadata, so it should be a dict
            # remove the metadata
            return {k: remove_ddb_format(v, this_is_metadata=True) for k, v in ddb_obj.items()}
    elif isinstance(ddb_obj, list):
        # this is a list, so we should remove the metadata
        return [remove_ddb_format(x, this_is_metadata=True) for x in ddb_obj]
    else:
        # this is a scalar, so we should return it
        return ddb_obj

def add_ddb_format(obj, add_to_this_level=False):
    print(f'add_ddb_format: {json.dumps(obj, indent=2)}')
    if add_to_this_level:
        if isinstance(obj, dict):
            return {"M": {k: add_ddb_format(v, add_to_this_level=True) for k, v in obj.items()}}
        elif isinstance(obj, (list, set, tuple)):
            return {"L": [add_ddb_format(x, add_to_this_level=True) for x in obj]}
        elif isinstance(obj, str):
            return {"S": obj}
        elif isinstance(obj, bool): # must be before int
            return {"BOOL": obj}
        elif isinstance(obj, (int, float)):
            return {"N": str(obj)}
        elif isinstance(obj, bytes):
            return {"B": obj}
        elif obj is None:
            return {"NULL": True} 
        else:
            raise ValueError(f'Unsupported type in obj: {type(obj)}')
    else:
        if isinstance(obj, dict):
            return {k: add_ddb_format(v, add_to_this_level=True) for k, v in obj.items()}
        elif isinstance(obj, (list, set, tuple)):
            return [add_ddb_format(x, add_to_this_level=True) for x in obj]
        else:
            # return obj
            raise ValueError(f'Expected container type but got {type(obj)}')

def remove_none_attribs(obj):
    '''
    Remove attributes from an object that are None.
    '''
    return {k: v for k, v in obj.items() if v is not None}

def calculate_key(pkey, skey, pkey_name, skey_name):
    '''
    Calculate the key for a dynamodb item.
    '''
    if skey_name is None:
        return add_ddb_format({pkey_name: pkey})
    else:
        return add_ddb_format({pkey_name: pkey, skey_name: skey})
    
def get_item(
    table_name, pkey, skey=None, pkey_name='pkey', skey_name=None, index_name=None, 
    consistent=False, return_consumed_capacity='NONE', projection_expression=None,
    expression_attribute_names=None
):
    '''
    Get an item from dynamodb.
    '''
    dynamodb_client = boto3.client('dynamodb')

    key = calculate_key(pkey, skey, pkey_name, skey_name)

    params = remove_none_attribs({
        'TableName': table_name,
        'IndexName': index_name,
        'Key': key,
        'ConsistentRead': consistent,
        'ReturnConsumedCapacity': return_consumed_capacity,
        'ProjectionExpression': projection_expression,
        'ExpressionAttributeNames': expression_attribute_names
    })

    print(f'params: {json.dumps(params, indent=2)}')

    response = dynamodb_client.get_item(**params)

    print(f'response: {json.dumps(response, indent=2)}')

    item = remove_ddb_format(response.get('Item')) if response.get('Item') else None

    adjusted_response = remove_none_attribs({
        'Item': item,
        'ConsumedCapacity': response.get('ConsumedCapacity')
    })

    return adjusted_response

def query(
    table_name, pkey, pkey_name='pkey', index_name=None, 
    select='ALL_ATTRIBUTES',
    consistent=False, forward=True, 
    return_consumed_capacity='NONE',
    key_condition_expression=None,
    projection_expression=None,
    filter_expression=None,
    expression_attribute_names=None,
    expression_attribute_values=None,
    cursor=None, limit=None
):

    print_dict = {
        "table_name": table_name,
        "pkey": pkey,
        "pkey_name": pkey_name,
        "index_name": index_name,
        "select": select,
        "consistent": consistent,
        "forward": forward,
        "return_consumed_capacity": return_consumed_capacity,
        "key_condition_expression": key_condition_expression,
        "projection_expression": projection_expression,
        "filter_expression": filter_expression,
        "expression_attribute_names": expression_attribute_names,
        "expression_attribute_values": expression_attribute_values,
        "cursor": cursor,
        "limit": limit
    }

    print(f'query(): {json.dumps(print_dict, indent=2)}')

    dynamodb_client = boto3.client('dynamodb')

    # if we have a cursor, it is the base64 encoded string of the json of last returned item
    exclusive_start_key = json.loads(base64.b64decode(cursor).decode('utf-8')) if cursor else None

    if key_condition_expression:
        use_key_condition_expression = f'{key_condition_expression} AND #pkey = :pkey'
    else:
        use_key_condition_expression = f'#pkey = :pkey'

    use_expression_attribute_names = {
        **(expression_attribute_names or {}),
        '#pkey': pkey_name
    }

    use_expression_attribute_values = add_ddb_format({
        **(expression_attribute_values or {}),
        ':pkey': pkey
    }) 

    # create a dictionary with all the parameters for the query
    params = remove_none_attribs({
        'TableName': table_name,
        'IndexName': index_name,
        'KeyConditionExpression': use_key_condition_expression,
        'ExpressionAttributeNames': use_expression_attribute_names,
        'ExpressionAttributeValues': use_expression_attribute_values,
        'Select': select,
        'ConsistentRead': consistent,
        'ScanIndexForward': forward,
        'ReturnConsumedCapacity': return_consumed_capacity,
        'ProjectionExpression': projection_expression,
        'FilterExpression': filter_expression,
        'Limit': int(limit or 20),
        'ExclusiveStartKey': exclusive_start_key,
    })

    # execute the query
    response = dynamodb_client.query(**params)

    print (f'query response: {response}')

    # the returned cursor is LastEvaluatedKey, json dumped and base64 encoded    
    cursor = base64.b64encode(json.dumps(response['LastEvaluatedKey']).encode(('utf-8'))).decode('utf-8') if 'LastEvaluatedKey' in response else None
    
    # if we have a cursor, it is the base64 encoded string of the json of last returned item
    adjusted_response = remove_none_attribs({
        'Items': [remove_ddb_format(x) for x in response['Items']],
        'Count': response.get('Count'),
        'ScannedCount': response.get('ScannedCount'),
        'Cursor': cursor,
        'ConsumedCapacity': response.get('ConsumedCapacity')
    })

    return adjusted_response

def put_item(
    table_name,
    item,
    condition_expression=None,
    expression_attribute_names=None,
    expression_attribute_values=None,
    return_values='NONE',
    return_consumed_capacity='NONE',
    return_item_collection_metrics='NONE'
):
    dynamodb_client = boto3.client('dynamodb')

    use_item = add_ddb_format(item)

    use_expression_attribute_values = {
        key: add_ddb_format(value) for key, value in expression_attribute_values.items()
    } if expression_attribute_values else None

    params = remove_none_attribs({
        'TableName': table_name,
        'Item': use_item,
        'ConditionExpression': condition_expression,
        'ExpressionAttributeNames': expression_attribute_names,
        'ExpressionAttributeValues': use_expression_attribute_values,
        'ReturnValues': return_values,
        'ReturnConsumedCapacity': return_consumed_capacity,
        'ReturnItemCollectionMetrics': return_item_collection_metrics,
    })

    response = dynamodb_client.put_item(**params)

    if "Attributes" in response:
        response["Attributes"] = remove_ddb_format(response["Attributes"])

    print(f'put response: {response}')

    return response

def update_item(
    table_name,
    pkey,
    skey=None,
    pkey_name='pkey',
    skey_name=None,
    set_value=None,
    add_value=None,
    remove_list=None,
    condition_expression=None,
    expression_attribute_names=None,
    expression_attribute_values=None,
    return_values='ALL_NEW',
    return_consumed_capacity='NONE',
    return_item_collection_metrics='NONE'
):
    dynamodb_client = boto3.client('dynamodb')

    key = calculate_key(pkey, skey, pkey_name, skey_name)

    set_clause_list = [f'#{key_name} = :{key_name}' for key_name, _ in set_value.items()] if set_value else None
    add_clause_list = [f'#{key_name} = :{key_name}' for key_name, _ in add_value.items()] if add_value else None
    remove_clause_list = [f'#{key_name}' for key_name in remove_list] if remove_list else None

    update_expression_clauses = [
        f'SET {",".join(set_clause_list)}' if set_clause_list else None,
        f'ADD {",".join(add_clause_list)}' if add_clause_list else None,
        f'REMOVE {",".join(remove_clause_list)}' if remove_clause_list else None
    ]

    update_expression = " ".join(filter(None, update_expression_clauses))

    use_expression_names = {
        **(expression_attribute_names or {}),
        ** {
            f'#{key_name}': key_name for key_name in (
                list((set_value or {}).keys()) + 
                list((add_value or {}).keys()) + 
                list((remove_list or []))
            )
        }
    }

    use_expression_values = add_ddb_format({
        **(expression_attribute_values or {}),
        ** {
            f':{key_name}': key_value for key_name, key_value in {
                **(set_value or {}),
                **(add_value or {})
            }.items()
        }
    })

    params = remove_none_attribs({
        'TableName': table_name,
        'Key': key,
        'UpdateExpression': update_expression,
        'ConditionExpression': condition_expression,
        'ExpressionAttributeNames': use_expression_names,
        'ExpressionAttributeValues': use_expression_values,
        'ReturnValues': return_values,
        'ReturnConsumedCapacity': return_consumed_capacity,
        'ReturnItemCollectionMetrics': return_item_collection_metrics,
    })

    response = dynamodb_client.update_item(**params)

    print(f'update_item response: {response}')

    adjusted_response = remove_none_attribs({
        'Attributes': remove_ddb_format(response['Attributes']) if 'Attributes' in response else None,
        **({
            'ConsumedCapacity': response['ConsumedCapacity'],
        } if 'ConsumedCapacity' in response else {}),
        **({
            'ItemCollectionMetrics': {
                'ItemCollectionKey': remove_ddb_format(response['ItemCollectionMetrics']['ItemCollectionKey'], True),
                'SizeEstimateRangeGB': response['ItemCollectionMetrics']['SizeEstimateRangeGB']
            }
        } if 'ItemCollectionMetrics' in response else {})
    })

    return adjusted_response

def delete_item(
    table_name,
    pkey,
    skey=None,
    pkey_name='pkey',
    skey_name=None,
    condition_expression=None,
    expression_attribute_names=None,
    expression_attribute_values=None,
    return_values='NONE',
    return_consumed_capacity='NONE',
    return_item_collection_metrics='NONE'
):
    dynamodb_client = boto3.client('dynamodb')

    key = calculate_key(pkey, skey, pkey_name, skey_name)

    params = remove_none_attribs({
        'TableName': table_name,
        'Key': key,
        'ConditionExpression': condition_expression,
        'ExpressionAttributeNames': expression_attribute_names,
        'ExpressionAttributeValues': expression_attribute_values,
        'ReturnValues': return_values,
        'ReturnConsumedCapacity': return_consumed_capacity,
        'ReturnItemCollectionMetrics': return_item_collection_metrics,
    })

    response = dynamodb_client.delete_item(**params)

    print(f'delete_item response: {response}')

    adjusted_response = {
        'Attributes': remove_ddb_format(response['Attributes']) if 'Attributes' in response else None,
        **({
            'ConsumedCapacity': response['ConsumedCapacity'],
        } if 'ConsumedCapacity' in response else {}),
        **({
            'ItemCollectionMetrics': {
                'ItemCollectionKey': remove_ddb_format(response['ItemCollectionMetrics']['ItemCollectionKey'], True),
                'SizeEstimateRangeGB': response['ItemCollectionMetrics']['SizeEstimateRangeGB']
            }
        } if 'ItemCollectionMetrics' in response else {})
    }

    return adjusted_response



                
