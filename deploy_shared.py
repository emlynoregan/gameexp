# from dis import dis
# from textwrap import indent
# from xml import dom
import boto3
import json
import botocore
import zipfile
import os
import time
import re
import shutil

C_APPCODE = 'spl'

C_LAMBDA_FUNCTION_NAME = f'{C_APPCODE}-lambda'
C_BLAMBDA_FUNCTION_NAME = f'{C_APPCODE}-blambda'
C_LAYER_NAME = f'{C_APPCODE}-layer'
C_QUEUE_NAME = f'{C_APPCODE}-queue.fifo'
C_BUCKET_NAME = f'{C_APPCODE}-bucket'
C_TABLE_NAME = f'{C_APPCODE}-table'
C_LAMBDA_ROLE_NAME = f'{C_APPCODE}-role'
C_DISTRIBUTION_REF = f'{C_APPCODE}-distribution'
C_OAI_REF = f'{C_APPCODE}-oai'
C_SECRET_REF = f'{C_APPCODE}-secret'
C_POLICY_REF = f'{C_APPCODE}-policy'
C_CERTIFICATE_REF = f'{C_APPCODE}-certificate'
C_HZ_REF = f'{C_APPCODE}-hz'

def get_lambda_function_name(prefix):
    return f"{prefix or 'def'}-{C_LAMBDA_FUNCTION_NAME}"

def get_background_lambda_function_name(prefix):
    return f"{prefix or 'def'}-{C_BLAMBDA_FUNCTION_NAME}"

def get_layer_name(prefix):
    return f"{prefix or 'def'}-{C_LAYER_NAME}"

def get_lambda_function_description(prefix):
    return f"Player Lambda ({prefix or 'def'})"

def get_background_lambda_function_description(prefix):
    return f"Player Background Lambda ({prefix or 'def'})"

def get_layer_description(prefix):
    return f"Player Layer ({prefix or 'def'})"

def get_queue_name(prefix):
    return f"{prefix or 'def'}-{C_QUEUE_NAME}"

def get_bucket_name(session, prefix):
    account_name = session.client('sts').get_caller_identity()['Account']
    # now convert all non-alphanumeric characters to dashes
    account_name_converted = re.sub('[^0-9a-zA-Z]+', '-', account_name)
    return f"{prefix or 'def'}-{C_BUCKET_NAME}-{account_name_converted}"

def get_full_bucket_name(session, prefix):
    return f"{get_bucket_name(session, prefix)}.s3.amazonaws.com"

def get_lambda_role_name(prefix):
    return f"{prefix or 'def'}-{C_LAMBDA_ROLE_NAME}"

def get_lambda_role_description(prefix):
    return f"Role for the Player Lambda ({prefix or 'def'})"

def get_table_name(prefix):
    return f"{prefix or 'def'}-{C_TABLE_NAME}"

def get_distribution_caller_reference(prefix):
    return f"{prefix or 'def'}-{C_DISTRIBUTION_REF}"

def get_secret_name(prefix):
    return f"{prefix or 'def'}-{C_SECRET_REF}"

def get_policy_name(prefix):
    return f"{prefix or 'def'}-{C_POLICY_REF}"

def get_certificate_name(prefix):
    return f"{prefix or 'def'}-{C_CERTIFICATE_REF}"

# def get_distribution_arn(distribution):
#     cloudfront_arn = distribution['ARN']

def get_origin_access_identity_caller_reference(prefix):
    return f"{prefix or 'def'}-{C_OAI_REF}"

def get_hosted_zone_caller_reference(prefix):
    return f"{prefix or 'def'}-{C_HZ_REF}"

###################################################################
###################################################################
#
# Utilities
#
###################################################################
###################################################################

def zip_directory(directory, zipfilename):
    with zipfile.ZipFile(zipfilename, 'w') as zip_file:
        for root, dirs, files in os.walk(directory):
            for file in files:
                zip_file.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), directory))

def WaitForComplete(check_function):
    while not check_function():
        print("Waiting...")
        time.sleep(2)

def GetConfigValue(prefix, attrname):
    # read the dictionary from config.json
    with open(f'config_{prefix}.json') as f:
        config = json.load(f)
    
    return config[attrname]

def is_deep_subset(subset_obj, main_obj):
    # first check that types match
    if type(subset_obj) != type(main_obj):
        return False

    # now handle dicts, lists, and simple types.
    if isinstance(subset_obj, dict):
        for key, value in subset_obj.items():
            if key not in main_obj:
                return False
            if not is_deep_subset(value, main_obj[key]):
                return False
        # if we got here, all keys matched
    elif isinstance(subset_obj, list):
        # compare lengths
        if len(subset_obj) != len(main_obj):
            return False
        # compare each element
        for i in range(len(subset_obj)):
            if not is_deep_subset(subset_obj[i], main_obj[i]):
                return False
    elif subset_obj != main_obj:
        return False

    return True

def get_credentials():
    # open the file credentials.json
    credentials = {}
    with open('credentials.json') as f:
        credentials = json.load(f)

    return credentials

def get_aws_credentials():
    credentials = get_credentials()

    aws_credentials = {
        "region_name": credentials['region_name'],
        "aws_access_key_id": credentials['aws_access_key_id'],
        "aws_secret_access_key": credentials['aws_secret_access_key'],
    }
    return aws_credentials

def get_session(aws_credentials):
    return boto3.session.Session(**aws_credentials)


def CreateOrUpdateSecret(session, SecretName):
    sm_client = session.client('secretsmanager')

    try:
        print("Creating secret...")
        sm_client.create_secret(
            Name=SecretName,
            SecretString="-"
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceExistsException':
            print("Secret already exists. Skipping...")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            print("Secret name was deleted too recently, Skipping...")
        else:
            raise e

def CreateOrUpdateRole(session, RoleName, Description, PolicyName):
    iam_client = session.client('iam')

    role_arn = None 

    try:
        print("Creating role...")
        result = iam_client.create_role(
            RoleName=RoleName,
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }),
            Description=Description
        )

        # wait 5 seconds as new roles need a bit of time to be created
        print("Waiting 10 seconds for role to be ready...")
        time.sleep(10)

        role_arn = result['Role']['Arn']
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print("Role already exists. Skipping...")
            # try updating the role
            iam_client.update_role(
                RoleName=RoleName,
                Description=Description
            )

            # now get the role so we can get the arn
            result = iam_client.get_role(
                RoleName=RoleName
            )

            role_arn = result['Role']['Arn']
        else:
            raise e

    # # attach the role policy
    # print("Attaching the AdministratorAccess policy...")
    # iam_client.attach_role_policy(
    #     RoleName=RoleName,
    #     PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess",
    # )

    # attach the basic logging policy
    print("Attaching the AWSLambdaBasicExecutionRole policy...")
    iam_client.attach_role_policy(
        RoleName=RoleName,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    
    # attach the custom policy
    if PolicyName:
        account_id = session.client('sts').get_caller_identity()['Account']
        policy_arn = f"arn:aws:iam::{account_id}:policy/{PolicyName}"

        print("Attaching the custom policy...")
        iam_client.attach_role_policy(
            RoleName=RoleName,
            PolicyArn=policy_arn,
        )

    return role_arn

def GetRoleArn(session, RoleName):
    iam_client = session.client('iam')

    try:
        print("Getting role...")
        result = iam_client.get_role(
            RoleName=RoleName
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print("Role does not exist. Skipping...")
            return None
        else:
            raise e

    return result['Role']['Arn']

def GetCustomPolicy(session, PolicyName):
    iam_client = session.client('iam')

    account_id = session.client('sts').get_caller_identity()['Account']
    policy_arn = f"arn:aws:iam::{account_id}:policy/{PolicyName}"

    try:
        print("Getting custom policy...")
        response = iam_client.get_policy(
            PolicyArn=policy_arn
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print("Custom policy does not exist. Skipping...")
            return None
        else:
            raise e

    return response['Policy']

def CreateOrUpdateCustomPolicy(session, policy_name, table_name, queue_name, secret_name, bucket_name):
    iam_client = session.client('iam')

    policy = GetCustomPolicy(session, policy_name)

    # calculated policy document should allow full access to the table, queue and secret
    account_id = session.client('sts').get_caller_identity()['Account']
    region = session.region_name
    table_arn = f"arn:aws:dynamodb:{region}:{account_id}:table/{table_name}"
    
    queue_arn = f"arn:aws:sqs:{region}:{account_id}:{queue_name}"
    secret_arn = f"arn:aws:kms:{region}:{account_id}:key/{secret_name}"
    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    calculated_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:*"
                ],
                "Resource": [
                    table_arn,
                    f"{table_arn}/*",
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "sqs:*"
                ],
                "Resource": [
                    queue_arn
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": [
                    secret_arn
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:*"
                ],
                "Resource": [
                    bucket_arn,
                    f"{bucket_arn}/*"
                ]
            }
        ]
    }

    if policy is None:
        print("Creating custom policy...")
        iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(calculated_policy_document)
        )
    else:
        account_id = session.client('sts').get_caller_identity()['Account']
        policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"  

        print("Get the previous policy versions")
        versions = iam_client.list_policy_versions(
            PolicyArn=policy_arn
        )

        print("Calculate the number of versions of this policy")
        version_count = len(versions['Versions'])

        print("Delete the oldest previous version if there are five or more.")
        if version_count >= 5:
            oldest_version = versions['Versions'][-1]
            iam_client.delete_policy_version(
                PolicyArn=policy_arn,
                VersionId=oldest_version['VersionId']
            )

        print("Now add a new policy version...")
        iam_client.create_policy_version(
            PolicyArn=policy_arn,
            PolicyDocument=json.dumps(calculated_policy_document),
            SetAsDefault=True
        )

def GetLambdaDeploymentCheck(session, lambda_name):
    def LambdaDeploymentCheck():
        lambda_client = session.client('lambda')

        response = lambda_client.get_function_configuration(
            FunctionName=lambda_name
        )

        print (f'Lambda LastUpdateStatus: {response["LastUpdateStatus"]}')

        return response['LastUpdateStatus'] == 'Successful'
    return LambdaDeploymentCheck

def CreateOrUpdateLambda(session, FunctionName, Description, CodePath, RoleArn, Handler, Env, LayerName):
    print (f"ENV: {Env}")
    lambda_client = session.client('lambda')

    zippath = f'ziptmp/{FunctionName}'
    zipfile = f'./{FunctionName}.zip'

    print("delete and then re-create a tmp folder to make the zip")
    # os.system(f'rm -rf {zippath}')
    # use shutil.rmtree instead of os.system to remove the folderCreateOrUpdateLambda
    shutil.rmtree(zippath, ignore_errors=True)

    os.makedirs(zippath, exist_ok=True)

    print("copy the contents of the code folder to the ziptmp folder")
    # cmd = f"cp -r {CodePath}/* {zippath}"
    # print(f'Executing: {cmd}')
    # os.system(cmd)
    # use shutil instead of os.system
    shutil.copytree(CodePath, zippath, dirs_exist_ok=True)

    # REMOVED: These are now in the layer
    # print("now install the requirements-for-deploy.txt file to the tmp folder")
    # os.system(f"pip install -r requirements-for-deploy.txt -t {zippath}")

    print("zip the ziptmp folder")
    zip_directory(zippath, zipfile)

    # get the configuration information for the lambda function
    deployed_code_size_bytes = None 
    lambda_exists = False
    try:
        response = lambda_client.get_function_configuration(
            FunctionName=FunctionName
        )

        lambda_exists = True
        print (f'response: {response}')
        deployed_code_size_bytes = response['CodeSize']
    
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            pass # no deployed lambda function, so we just use default deployed_code_size_bytes of None
        else:
            raise e

    # lambda_arn = response['FunctionArn']

    new_code_size_bytes = os.path.getsize(zipfile)
    print(f"new_code_size_bytes: {new_code_size_bytes}")
    print(f"deployed_code_size_bytes: {deployed_code_size_bytes}")

    # if the code size is the same, then we don't need to update the lambda function
    need_update_code = deployed_code_size_bytes != new_code_size_bytes
    print(f"need_update_code: {need_update_code}")

    latest_layer_version_arn = GetLatestLayerVersionArn(session, LayerName)

    # create the lambda
    if not lambda_exists:
        print("Creating lambda...")
        lambda_client.create_function(
            FunctionName=FunctionName,
            Runtime='python3.9',
            Role=RoleArn,
            Handler=Handler,
            Code={
                'ZipFile': open(zipfile, 'rb').read()
            },
            Description=Description,
            Timeout=300,
            MemorySize=1024,
            Publish=True, 
            Environment={
                'Variables': Env
            },
            Architectures=['arm64'],
            Layers=[
                latest_layer_version_arn
            ]
        )
    else:
        print("Lambda already exists. Updating...")

        WaitForComplete(GetLambdaDeploymentCheck(session, FunctionName))

        print("Updating function configuration...")
        lambda_client.update_function_configuration(
            FunctionName=FunctionName,
            Runtime='python3.9',
            Role=RoleArn,
            Handler=Handler,
            Description=Description,
            Timeout=300,
            MemorySize=1024,
            Environment={
                'Variables': Env
            },
            Layers=[
                latest_layer_version_arn
            ]
        )

        if need_update_code:
            WaitForComplete(GetLambdaDeploymentCheck(session, FunctionName))

            print("Updating function code...")
            lambda_client.update_function_code(
                FunctionName=FunctionName,
                ZipFile=open(zipfile, 'rb').read(),
                Publish=True
            )
        else:
            print("skipping code update, no change")

    # create function url config
    print("Creating function url config...")
    try:
        lambda_client.create_function_url_config(
            FunctionName=FunctionName,
            AuthType='NONE',
            Cors={
                'AllowCredentials': True,
                'AllowHeaders': [
                    '*'
                ],
                'AllowMethods': [
                    '*'
                ],
                'AllowOrigins': [
                    '*'
                ],
                'ExposeHeaders': [
                    '*'
                ],
                'MaxAge': 86400
            }
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            print("Function url config already exists")
        else:
            raise e

    # add permission to the function

    try:
        lambda_client.add_permission(
            FunctionName=FunctionName,
            StatementId='AllowPublicAccess',
            Action='lambda:InvokeFunctionUrl',
            Principal='*',
            # SourceArn=None,
            # SourceAccount=None,
            # EventSourceToken=None,
            # Qualifier=None,
            # RevisionId=None,
            FunctionUrlAuthType='NONE'
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            print("Function permission already exists")
        else:
            raise e

def GetLatestLayerVersion(session, LayerName):
    lambda_client = session.client('lambda')

    response = lambda_client.list_layer_versions(
        LayerName=LayerName
    )

    if len(response['LayerVersions']):
        return response['LayerVersions'][0]['Version']
    else:
        return None

def GetLatestLayerVersionArn(session, LayerName):
    lambda_client = session.client('lambda')

    response = lambda_client.list_layer_versions(
        LayerName=LayerName
    )

    if len(response['LayerVersions']):
        return response['LayerVersions'][0]['LayerVersionArn']
    else:
        return None
    

def CreateOrUpdateLayer(session, LayerName, Description, CodePath):
    lambda_client = session.client('lambda') #, verify=False)

    zippath = f'ziptmp/{LayerName}'
    zipfile = f'./{LayerName}.zip'

    print("delete and then re-create a tmp folder to make the zip")
    # os.system(f'rm -rf {zippath}')
    # use shutil.rmtree instead of os.system to remove the folder
    shutil.rmtree(zippath, ignore_errors=True)

    os.makedirs(zippath, exist_ok=True)

    print("copy the contents of the code folder to the ziptmp folder")
    # cmd = f"cp -r {CodePath}/* {zippath}"
    # print(f'Executing: {cmd}')
    # os.system(cmd)

    # use shutil to do the copy
    shutil.copytree(CodePath, zippath, dirs_exist_ok=True)

    print("now install the requirements-for-deploy.txt file to the tmp folder")
    os.system(f"pip install -r requirements-for-deploy.txt -t {zippath}")

    print("zip the ziptmp folder")
    zip_directory(zippath, zipfile)

    latest_layer_version = GetLatestLayerVersion(session, LayerName)

    if latest_layer_version is not None:
        # we need to figure out if the code has changed. If it has, then we need to update the layer.

        response = lambda_client.get_layer_version(
            LayerName=LayerName,
            VersionNumber=latest_layer_version
        )

        deployed_code_size_bytes = response['Content']['CodeSize']

        new_code_size_bytes = os.path.getsize(zipfile)

        need_update_code = deployed_code_size_bytes != new_code_size_bytes
    else:
        need_update_code = True

    if need_update_code:
        print("Creating layer version...")
        response = lambda_client.publish_layer_version(
            LayerName=LayerName,
            Description=Description,
            Content={
                'ZipFile': open(zipfile, 'rb').read()
            },
            CompatibleRuntimes=['python3.9']
        )

        latest_layer_version = response['Version']
    else:
        print("skipping layer update, no change")

    return latest_layer_version


def CalculateQueueUrl(session, QueueName):
    region_name = session.region_name
    account_id = session.client('sts').get_caller_identity()['Account']

    queue_url = f"https://sqs.{region_name}.amazonaws.com/{account_id}/{QueueName}"

    return queue_url

def CalculateQueueArn(session, QueueName):
    region_name = session.region_name
    account_id = session.client('sts').get_caller_identity()['Account']

    queue_arn = f"arn:aws:sqs:{region_name}:{account_id}:{QueueName}"

    return queue_arn


def GetQueuePolicy(session, QueueName):
    region_name = session.region_name

    return json.dumps({
        "Version": "2012-10-17",
        "Id": f"{region_name}-{QueueName}",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                # "Principal": {
                #     "AWS": "*"
                # },
                "Action": [
                    "sqs:SendMessage"
                ],
                "Resource": [
                    CalculateQueueArn(session, QueueName)
                ]
            }
        ]
    })

def CreateOrUpdateSQSQueue(session, QueueName):
    sqs_client = session.client('sqs')

    print("Creating SQS queue...")
    # message retention period is set to 2 hours
    # visibility timeout is set to 16 minutes (in seconds)

    def CreateQueueCheck():
        result = True
        try:
            sqs_client.create_queue(
                QueueName=QueueName,
                Attributes={
                    'Policy': GetQueuePolicy(session, QueueName),
                    'MessageRetentionPeriod': '7200',
                    'VisibilityTimeout': '960',
                    'FifoQueue': 'true',
                    'ContentBasedDeduplication': 'true',
                    'DeduplicationScope': 'messageGroup',
                    'FifoThroughputLimit': 'perMessageGroupId'
                }
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'QueueAlreadyExists':
                print("Queue already exists. Skipping...")
            elif e.response['Error']['Code'] == 'AWS.SimpleQueueService.QueueDeletedRecently':
                print("Queue was recently deleted. Waiting...")
                result = False
            else:
                print(e.response['Error']['Code'])
                raise e

        return result

    WaitForComplete(CreateQueueCheck)

def GetDynamoDBTableStatusCheck(session, TableName):
    def DynamoDBTableStatusCheck():
        dynamodb_client = session.client('dynamodb')

        result = dynamodb_client.describe_table(
            TableName=TableName
        )

        return result['Table']['TableStatus'] == 'ACTIVE'
    return DynamoDBTableStatusCheck

def CreateOrUpdateDynamoDBTable(session, TableName):
    dynamodb_client = session.client('dynamodb')

    try:
        print("Creating DynamoDB table...")

        # should be on-demand provisioned

        # should also have one GSI called lookup1 with string pkey and skey called l1_pkey and l1_skey
        dynamodb_client.create_table(
            TableName=TableName,
            KeySchema=[
                {
                    'AttributeName': 'pkey',
                    'KeyType': 'HASH'
                },
                # {
                #     'AttributeName': 'skey',
                #     'KeyType': 'RANGE'
                # }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'lookup1',
                    'KeySchema': [
                        {
                            'AttributeName': 'l1_pkey',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'l1_skey',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                },
                {
                    'IndexName': 'lookup2',
                    'KeySchema': [
                        {
                            'AttributeName': 'l2_pkey',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'l2_skey',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                },
                {
                    'IndexName': 'lookup3',
                    'KeySchema': [
                        {
                            'AttributeName': 'l3_pkey',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'l3_skey',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                },
                {
                    'IndexName': 'lookup4',
                    'KeySchema': [
                        {
                            'AttributeName': 'l4_pkey',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'l4_skey',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'pkey',
                    'AttributeType': 'S'
                },
                # {
                #     'AttributeName': 'skey',
                #     'AttributeType': 'S'
                # },
                {
                    'AttributeName': 'l1_pkey',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'l1_skey',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'l2_pkey',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'l2_skey',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'l3_pkey',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'l3_skey',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'l4_pkey',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'l4_skey',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("Table already exists. Skipping...")
        else:
            raise e

    WaitForComplete(GetDynamoDBTableStatusCheck(session, TableName))

    # we're going to add a ttl attribute to the table, called "ttl".

    response = dynamodb_client.describe_time_to_live(
        TableName=TableName
    )

    if response['TimeToLiveDescription']['TimeToLiveStatus'] == 'DISABLED':
        print("Enabling TTL...")
        dynamodb_client.update_time_to_live(
            TableName=TableName,
            TimeToLiveSpecification={
                'AttributeName': 'ttl',
                'Enabled': True
            }
        )
    else:
        print("TTL already enabled. Skipping...")

def CalculateBucketPolicy(session, oai_id, bucket_arn):
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": f"arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity {oai_id}"
                },
                "Action": "s3:GetObject",
                "Resource": f"{bucket_arn}/*"
            }
        ]
    }

def CreateOrUpdateS3Bucket(session, prefix, BucketName):
    '''
    The bucket must not be public. The bucket policy should lock it down.
    Block public access.
    '''
    s3_client = session.client('s3')

    oai = GetCloudFrontOriginAccessIdentity(session, prefix)

    oai_id = oai['CloudFrontOriginAccessIdentity']['Id']

    bucket_arn = f"arn:aws:s3:::{BucketName}"

    try:
        print(f"Creating S3 bucket ({BucketName})...")
        s3_client.create_bucket(
            Bucket=BucketName
        )

        # public access block
        print("Setting bucket public access block...")
        s3_client.put_public_access_block(
            Bucket=BucketName,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }
        )
        
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print("Bucket already exists. Skipping...")
            return
        elif e.response['Error']['Code'] == 'BucketAlreadyExists':
            raise 
        else:
            raise e

    print("Setting bucket policy...")
    bucket_policy = CalculateBucketPolicy(session, oai_id, bucket_arn)

    print(f"Bucket policy: {json.dumps(bucket_policy, indent=2)}")

    s3_client.put_bucket_policy(
        Bucket=BucketName,
        Policy=json.dumps(bucket_policy)
    )

    print(f"Put cors policy on bucket ({BucketName})...")
    s3_client.put_bucket_cors(
        Bucket=BucketName,
        CORSConfiguration={
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['PUT', 'POST', 'GET', 'DELETE', 'HEAD'],
                    'AllowedOrigins': ['*'],
                    'ExposeHeaders': ['ETag'],
                    'MaxAgeSeconds': 86400
                }
            ]
        }
    )

def GetCloudFrontDistributionStatusCheck(session, prefix, status=None):
    def CloudFrontDistributionStatusCheck():
        distribution = GetCloudFrontDistribution(session, prefix)

        if not distribution:
            raise Exception("No distribution found.")

        print(f'Distribution status: {distribution["Status"]}')

        return distribution['Status'] == (status or 'Deployed')
    return CloudFrontDistributionStatusCheck

def GetCloudFrontDistributionEnabledCheck(session, prefix, enabled=True):
    def CloudFrontDistributionEnabledCheck():
        distribution = GetCloudFrontDistribution(session, prefix)

        if not distribution:
            raise Exception("No distribution found.")

        print(f'Distribution enabled: {distribution["Enabled"]}')

        return distribution['Enabled'] == enabled
    return CloudFrontDistributionEnabledCheck

def GetCloudFrontDistribution(session, prefix):
    cloudfront_client = session.client('cloudfront')

    caller_reference = get_distribution_caller_reference(prefix)

    result = cloudfront_client.list_distributions()

    marker = result.get('NextMarker')

    while result:
        distributions = result['DistributionList'].get('Items') or []
        for distribution in distributions:
            # the distribution we are looking for has a ref tag whose value is 
            # the distribution caller reference.

            result = cloudfront_client.list_tags_for_resource(
                Resource=distribution['ARN']
            )

            tags_dict = {
                tag['Key']: tag['Value']
                for tag in result['Tags']['Items']
            }

            print (f"Tags: {tags_dict}, looking for ref={caller_reference}")

            if tags_dict.get('ref') == caller_reference:
                print (f"Found distribution")

                return distribution
        
        # didn't find it, so get the next page
        if marker:
            result = cloudfront_client.list_distributions(
                Marker=marker
            )
            marker = result.get('NextMarker')
        else:
            break

    print ("Did not find distribution")
    return None

def CalculateDistributionConfig(caller_reference, full_bucket_name, domain_name, oai_id = None, existing_distribution_config=None, certificate_arn=None):
    print (f"existing_distribution_config: {json.dumps(existing_distribution_config, indent=2)}")
    print (f"oai_id: {oai_id}")
    result = {
        **(existing_distribution_config or {}),
        **{
            'CallerReference': caller_reference,
            'Aliases': {
                'Quantity': 1,
                'Items': [
                    domain_name
                ]
            },
            'DefaultRootObject': 'index.html',
            'Origins': {
                'Quantity': 2,
                'Items': [
                    {
                        'Id': 'Content-Origin',
                        'DomainName': full_bucket_name,
                        'OriginPath': '',
                        "CustomHeaders": {
                            "Quantity": 0
                        },
                        'S3OriginConfig': {
                            'OriginAccessIdentity': f"origin-access-identity/cloudfront/{oai_id}" or ''
                        },
                    },
                    {
                        'Id': 'S3-Origin',
                        'DomainName': full_bucket_name,
                        'OriginPath': '/ui',
                        "CustomHeaders": {
                            "Quantity": 0
                        },
                        'S3OriginConfig': {
                            'OriginAccessIdentity': f"origin-access-identity/cloudfront/{oai_id}" or ''
                        },
                    },
                ]
            },
            'DefaultCacheBehavior': {
                'TargetOriginId': 'S3-Origin',
                'ViewerProtocolPolicy': 'redirect-to-https',
                'TrustedSigners': {
                    'Quantity': 0,
                    'Enabled': False
                },
                'ForwardedValues': {
                    'Cookies': {
                        'Forward': 'all'
                    },
                    'Headers': {
                        'Quantity': 0
                    },
                    'QueryString': False,
                    'QueryStringCacheKeys': {
                        'Quantity': 0
                    }
                },
                'DefaultTTL': 86400,
                'MinTTL': 0,
                'MaxTTL': 31536000,
                'SmoothStreaming': False,
                'Compress': False,
                "FieldLevelEncryptionId": "",
                "AllowedMethods": {
                    "Quantity": 2,
                    "Items": [
                        "HEAD",
                        "GET"
                    ],
                    "CachedMethods": {
                        "Quantity": 2,
                        "Items": [
                        "HEAD",
                        "GET"
                        ]
                    }
                },
                "LambdaFunctionAssociations": {
                    "Quantity": 0
                },
            },
            'CacheBehaviors': {
                'Quantity': 1,
                'Items': [
                    {
                        'TargetOriginId': 'Content-Origin',
                        'PathPattern': 'content/*',
                        'ViewerProtocolPolicy': 'redirect-to-https',
                        'TrustedSigners': {
                            'Quantity': 0,
                            'Enabled': False
                        },
                        'ForwardedValues': {
                            'Cookies': {
                                'Forward': 'all'
                            },
                            'Headers': {
                                'Quantity': 0
                            },
                            'QueryString': False,
                            'QueryStringCacheKeys': {
                                'Quantity': 0
                            }
                        },
                        'DefaultTTL': 86400,
                        'MinTTL': 0,
                        'MaxTTL': 31536000,
                        'SmoothStreaming': False,
                        'Compress': False,
                        "FieldLevelEncryptionId": "",
                        "AllowedMethods": {
                            "Quantity": 2,
                            "Items": [
                                "HEAD",
                                "GET"
                            ],
                            "CachedMethods": {
                                "Quantity": 2,
                                "Items": [
                                "HEAD",
                                "GET"
                                ]
                            }
                        },
                        "LambdaFunctionAssociations": {
                            "Quantity": 0
                        }
                    }
                ]
            },
            'Comment': '',
            'Enabled': True,
            'PriceClass': 'PriceClass_100',
            'ViewerCertificate': {
                'CloudFrontDefaultCertificate': True,
                "MinimumProtocolVersion": "TLSv1"
            },
            'Restrictions': {
                'GeoRestriction': {
                    'RestrictionType': 'none',
                    'Quantity': 0
                }
            },
            'ViewerCertificate': {
                'CloudFrontDefaultCertificate': False,
                'ACMCertificateArn': certificate_arn,
                'SSLSupportMethod': 'sni-only',
                'MinimumProtocolVersion': 'TLSv1',
            },
            'CustomErrorResponses': {
                'Quantity': 2,
                'Items': [
                    {
                        'ErrorCode': 403,
                        'ResponsePagePath': '/index.html',
                        'ResponseCode': '200',
                        'ErrorCachingMinTTL': 300
                    },
                    {
                        'ErrorCode': 404,
                        'ResponsePagePath': '/index.html',
                        'ResponseCode': '200',
                        'ErrorCachingMinTTL': 300
                    },
                ]
            }
        }
    }

    return result

def CreateOrUpdateCloudFrontOriginAccessIdentity(session, prefix):
    cloudfront_client = session.client('cloudfront')

    origin_access_identity = GetCloudFrontOriginAccessIdentity(session, prefix)

    if not origin_access_identity:
        # create the origin identity
        print("Creating origin identity...")
        result = cloudfront_client.create_cloud_front_origin_access_identity(
            CloudFrontOriginAccessIdentityConfig={
                'CallerReference': get_origin_access_identity_caller_reference(prefix),
                'Comment': 'caller_reference: ' + get_origin_access_identity_caller_reference(prefix)
            }
        )

        origin_access_identity = result

    # note: different format if get or create. Check boto3 reference for details.
    print(f"Origin access identity: {origin_access_identity}")

def GetCloudFrontOriginAccessIdentity(session, prefix):
    cloudfront_client = session.client('cloudfront')

    caller_reference = get_origin_access_identity_caller_reference(prefix)

    result = cloudfront_client.list_cloud_front_origin_access_identities()

    marker = result.get('NextMarker')

    while result:
        origin_access_identities = result['CloudFrontOriginAccessIdentityList'].get('Items') or []
        for origin_access_identity in origin_access_identities:
            # the origin access identity we are looking for has a comment containing
            # the caller reference.

            oai_comment = origin_access_identity['Comment']

            found = oai_comment.find(caller_reference) >= 0

            if found:
                print (f"Found origin access identity")

                # now call get_cloud_front_origin_access_identity to get the full result
                result = cloudfront_client.get_cloud_front_origin_access_identity(
                    Id=origin_access_identity['Id']
                )

                return result

                return origin_access_identity
                    
        # didn't find it, so get the next page
        if marker:
            result = cloudfront_client.list_cloud_front_origin_access_identities(
                Marker=marker
            )
            marker = result.get('NextMarker')
        else:
            break

    print ("Did not find origin access identity")
    return None


def CreateOrUpdateCloudFrontDistribution(session, prefix, full_bucket_name, domain_name, oai_id):
    '''
    Create or update CloudFront distribution.
    '''
    cloudfront_client = session.client('cloudfront')
    caller_reference = get_distribution_caller_reference(prefix)
    distribution = GetCloudFrontDistribution(session, prefix)

    certificate = None
    while not certificate:
        certificate = GetCertificate(session, prefix)
        if not certificate:
            print("Waiting for certificate...")
            time.sleep(5)

    if distribution:
        arn = distribution['ARN']

        print(f"Get the distribution config for the etag")
        result = cloudfront_client.get_distribution_config(
            Id=distribution['Id']
        )

        etag = result['ETag']
        # arn = result['DistributionConfig']['ARN']
        existing_distribution_config = result.get('DistributionConfig')

        distribution_config = CalculateDistributionConfig(caller_reference, full_bucket_name, domain_name, existing_distribution_config=existing_distribution_config, oai_id=oai_id, certificate_arn=certificate['CertificateArn'])

        print(f"distribution_config: {json.dumps(distribution_config, indent=2)}")
        print(f"existing_distribution_config: {json.dumps(existing_distribution_config, indent=2)}")

        if not is_deep_subset(distribution_config, existing_distribution_config):
            print(f"Updating CloudFront distribution ({distribution['Id']})...")
            result = cloudfront_client.update_distribution(
                Id=distribution['Id'],
                IfMatch=etag,
                DistributionConfig=distribution_config
            )

        cloudfront_client.tag_resource(
            Resource=arn,
            Tags={
                'Items': [
                    {
                        'Key': 'ref',
                        'Value': caller_reference
                    }
                ]
            }
        )
    else:
        print("Creating CloudFront distribution...")
        distribution_config = CalculateDistributionConfig(caller_reference, full_bucket_name, domain_name, oai_id=oai_id, certificate_arn=certificate['CertificateArn'])

        cloudfront_client.create_distribution_with_tags(
            DistributionConfigWithTags={
                'DistributionConfig': distribution_config,
                'Tags': {
                    'Items': [
                        {
                            'Key': 'ref',
                            'Value': caller_reference
                        }
                    ]
                }
            }
        )

    WaitForComplete(GetCloudFrontDistributionStatusCheck(session, prefix))

def AddQueueEventSourceMapping(session, QueueName, LambdaName):
    lambda_client = session.client('lambda')

    # get the queue arn
    queue_arn = CalculateQueueArn(session, QueueName)

    # create the event source mapping
    print("Creating event source mapping...")
    try:
        done = False
        while not done:
            try:
                lambda_client.create_event_source_mapping(
                    EventSourceArn=queue_arn,
                    FunctionName=LambdaName,
                    FunctionResponseTypes=['ReportBatchItemFailures'],
                )
                done = True
            except Exception as e:
                if e.response['Error']['Code'] == 'InvalidParameterValueException':
                    print("Role not ready, waiting 5 seconds...")
                    time.sleep(5)
                else:
                    raise e
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            print("Event source mapping already exists. Skipping...")
        else:
            raise e

def CalculateCertificateArn(session, prefix):
    '''
    Calculate the certificate ARN.
    '''
    account_id = session.client('sts').get_caller_identity()['Account']
    region = session.region_name
    certificate_name = get_certificate_name(prefix)
    return f"arn:aws:acm:{region}:{account_id}:certificate/{certificate_name}"

def GetCertificate(session, prefix):
    '''
    Get the certificate.
    '''
    acm_client = session.client('acm')

    domain_name = GetConfigValue(prefix, 'domain_name')

    # list all the certificates, looking for our domain name

    result = acm_client.list_certificates()

    marker = result.get('NextToken')

    while result:
        certificates = result['CertificateSummaryList'] or []
        for certificate in certificates:
            # our domain name could be the same as the certificate name, or it could be a
            # subdomain of the certificate name and the certificate name has a wildcard

            if "*" in certificate['DomainName']:
                # remove the wildcard
                cert_name = certificate['DomainName'].replace("*.", "")
                matches = domain_name.endswith(cert_name)
            else:
                matches = certificate['DomainName'] == domain_name

            if matches:
                result_c = acm_client.describe_certificate(
                    CertificateArn=certificate['CertificateArn']
                )

                return result_c['Certificate']

        # didn't find it, so get the next page
        if marker:
            result = acm_client.list_certificates(
                NextToken=marker
            )
            marker = result.get('NextToken')
        else:
            break

    return None

def CreateOrUpdateCertificate(session, prefix):
    acm_client = session.client('acm')

    # get the certificate arn
    certificate_arn = CalculateCertificateArn(session, prefix)

    certificate = GetCertificate(session, prefix)

    if not certificate:
        print("Creating certificate...")
        domain_name = GetConfigValue(prefix, "domain_name")

        acm_client.request_certificate(
            DomainName=domain_name,
            ValidationMethod='DNS'
        )
    else:
        print("Certificate already exists. Skipping...")

def GetHostedZone(session, domain_name):
    route53_client = session.client('route53')

    result = route53_client.list_hosted_zones()

    marker = result.get('NextMarker')

    while result:
        hosted_zones = result['HostedZones'] or []
        for hosted_zone in hosted_zones:
            print(f"Checking hosted zone {hosted_zone['Name']}")
            if hosted_zone['Name'] == f"{domain_name}.":
                return hosted_zone

        # didn't find it, so get the next page
        if marker:
            result = route53_client.list_hosted_zones(
                Marker=marker
            )
            marker = result.get('NextMarker')
        else:
            break

    return None

def CreateOrUpdateHostedZone(session, prefix):
    # try to get the hosted zone
    domain_name = GetConfigValue(prefix, 'domain_name')
    hosted_zone = GetHostedZone(session, domain_name)

    if not hosted_zone:
        # create the hosted zone
        route53_client = session.client('route53')

        print("Creating hosted zone...")
        caller_reference = get_hosted_zone_caller_reference(prefix)

        result = route53_client.create_hosted_zone(
            Name=domain_name,
            CallerReference=caller_reference,
            HostedZoneConfig={
                "Comment": f"cr={caller_reference}, domain={domain_name}",
                "PrivateZone": False
            }
        )

        hosted_zone = result['HostedZone']
    else:
        print("Hosted zone already exists. Skipping...")

def CreateOrUpdateRoute53ResourceRecords(session, prefix):
    domain_name = GetConfigValue(prefix, 'domain_name')
    hosted_zone = GetHostedZone(session, domain_name)
    
    # let's just list all the route53 resource records
    route53_client = session.client('route53')

    result = route53_client.list_resource_record_sets(
        HostedZoneId=hosted_zone['Id']
    )

    marker = result.get('NextMarker')

    while result:
        resource_records = result['ResourceRecordSets'] or []
        for resource_record in resource_records:
            print(resource_record)

        # didn't find it, so get the next page
        if marker:
            result = route53_client.list_resource_record_sets(
                HostedZoneId=hosted_zone['Id'],
                StartRecordName=marker
            )
            marker = result.get('NextMarker')
        else:
            break


    distribution = GetCloudFrontDistribution(session, prefix)

    # UPSERT the A and AAAA records
    route53_client = session.client('route53')

    C_CLOUDFRONT_HOSTED_ZONE_ID = "Z2FDTNDATAQYW2" # a fixed value for CloudFront

    changes = [
        {
            'Action': 'UPSERT',
            'ResourceRecordSet': {
                'Name': domain_name,
                'Type': 'A',
                'AliasTarget': {
                    'HostedZoneId': C_CLOUDFRONT_HOSTED_ZONE_ID,
                    'DNSName': distribution['DomainName'],
                    'EvaluateTargetHealth': False
                }
            }
        },
        {
            'Action': 'UPSERT',
            'ResourceRecordSet': {
                'Name': domain_name,
                'Type': 'AAAA',
                'AliasTarget': {
                    'HostedZoneId': C_CLOUDFRONT_HOSTED_ZONE_ID,
                    'DNSName': distribution['DomainName'],
                    'EvaluateTargetHealth': False
                }
            }
        }
    ]

    print (f"Changes: {changes}") 
    print("Creating route53 resource records...")
    route53_client.change_resource_record_sets(
        HostedZoneId=hosted_zone['Id'],
        ChangeBatch={
            'Changes': changes
        }
    )

def DeleteCustomPolicy(session, prefix):
    iam_client = session.client('iam')
    policy_name = get_policy_name(prefix)
    policy = GetCustomPolicy(session, policy_name)
    if policy:
        policy_arn = policy['Arn']

        # get the policy versions
        policy_versions = iam_client.list_policy_versions(
            PolicyArn=policy_arn
        )

        # for each policy version, delete the policy version if it is not default.
        for policy_version in policy_versions['Versions']:
            if policy_version['IsDefaultVersion'] == False:
                iam_client.delete_policy_version(
                    PolicyArn=policy_arn,
                    VersionId=policy_version['VersionId']
                )

        print("Deleting custom policy...")
        iam_client.delete_policy(PolicyArn=policy_arn)
    else:
        print("No custom policy to delete")

def DeleteSecret(session, prefix):
    client = session.client('secretsmanager')
    secret_name = get_secret_name(prefix)
    try:
        print("Deleting secret...")
        client.delete_secret(SecretId=secret_name)
    except client.exceptions.ResourceNotFoundException:
        print("Secret not found. Skipping...")

def DeleteDynamoDBTable(session, table_name):
    try:
        dynamodb_client = session.client('dynamodb')
        dynamodb_client.delete_table(TableName=table_name)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("Table does not exist. Skipping...")
        else:
            raise e

def DeleteS3Bucket(session, bucket_name):
    try:
        s3_client = session.client('s3')
        s3_client.delete_bucket(Bucket=bucket_name)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print("Bucket does not exist. Skipping...")
        else:
            raise e

def DeleteEventSourceMappings(session, function_name):
    lambda_client = session.client('lambda')
    
    # first find the event source mapping
    response = lambda_client.list_event_source_mappings(
        FunctionName=function_name
    )

    for mapping in response['EventSourceMappings']:
        print(f"Deleting event source mapping {mapping['UUID']}")
        try:
            lambda_client.delete_event_source_mapping(
                UUID=mapping['UUID']
            )
        except botocore.exceptions.ClientError as e:
            # just skip it
            print(f'failed to delete event source mapping {mapping["UUID"]}, skipping...')

def DeleteQueue(session, queue_name):
    try:
        sqs_client = session.client('sqs')
        queue_url = CalculateQueueUrl(session, queue_name)
        sqs_client.delete_queue(QueueUrl=queue_url)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
            print("Queue does not exist. Skipping...")
        else:
            raise e

def DeleteLambda(session, function_name):
    try:
        lambda_client = session.client('lambda')
        lambda_client.delete_function(
            FunctionName=function_name
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("Lambda not found. Skipping...")
        else:
            raise e

def DeleteLayer(session, layer_name):
    try:
        lambda_client = session.client('lambda')

        # list all the layer versions, then delete each one individually
        print (f"Listing layer versions for {layer_name}...")
        response = lambda_client.list_layer_versions(
            LayerName=layer_name
        )

        for layer_version in response['LayerVersions']:
            print(f"Deleting layer version {layer_version['Version']} for {layer_name}...")

            lambda_client.delete_layer_version(
                LayerName=layer_name,
                VersionNumber=layer_version['Version']
            )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("Layer not found. Skipping...")
        else:
            raise e

def GetRole(session, role_name):
    iam_client = session.client('iam')
    try:
        response = iam_client.get_role(
            RoleName=role_name
        )
        return response
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            return None
        else:
            raise e

def DeleteRole(session, role_name):
    print ("** First detach all role policies...")
    iam_client = session.client('iam')

    # get the role
    role = GetRole(session, role_name)

    if role:
        # for all policies attached to this role, detach the policy
        response = iam_client.list_attached_role_policies(
            RoleName=role_name
        )
        for policy in response['AttachedPolicies']:
            print(f"Detaching policy {policy['PolicyName']}")
            iam_client.detach_role_policy(
                RoleName=role_name,
                PolicyArn=policy['PolicyArn']
            )

        print("** Now deleting the lambda role...")
        iam_client.delete_role(
            RoleName=role_name
        )
    else:
        print("No role to delete")

def DeleteCloudFrontDistribution(session, prefix, full_bucket_name):
    cloudfront_client = session.client('cloudfront')

    distribution = GetCloudFrontDistribution(session, prefix)
    print(f"Distribution: {distribution}")

    if distribution is None:
        print(f"Distribution not found. Skipping...")
        return

    # arn = distribution['ARN']

    distribution_id = distribution['Id']

    result = cloudfront_client.get_distribution_config(
        Id=distribution_id
    )

    etag = result['ETag']

    caller_reference = get_distribution_caller_reference(prefix)

    if not result['DistributionConfig']['Enabled']:
        print("We have to re-enable the CloudFront distribution...")
        updated_distribution_config = {**result.get('DistributionConfig')}

        updated_distribution_config['Enabled'] = True

        cloudfront_client.update_distribution(
            Id=distribution_id,
            IfMatch=etag,
            DistributionConfig=updated_distribution_config
        )

        result = cloudfront_client.get_distribution_config(
            Id=distribution_id
        )

        etag = result['ETag']

    WaitForComplete(GetCloudFrontDistributionStatusCheck(session, prefix))

    # result = cloudfront_client.get_distribution_config(
    #     Id=distribution_id
    # )
    
    # print(f'result: {result}')

    # distribution_config = result['DistributionConfig']

    # etag = result['ETag']

    print("Disabling CloudFront distribution")
    updated_distribution_config = {**result.get('DistributionConfig')}

    updated_distribution_config['Enabled'] = False

    cloudfront_client.update_distribution(
        Id=distribution_id,
        IfMatch=etag,
        DistributionConfig=updated_distribution_config
    )

    result = cloudfront_client.get_distribution_config(
        Id=distribution_id
    )

    etag = result['ETag']

    # wait for the distribution to be disabled
    print("Waiting for CloudFront distribution to be disabled...")
    WaitForComplete(GetCloudFrontDistributionEnabledCheck(session, prefix, False))

    WaitForComplete(GetCloudFrontDistributionStatusCheck(session, prefix))

    cloudfront_client.delete_distribution(
        Id=distribution_id,
        IfMatch=etag
    )

def DeleteCertificate(session, prefix):
    acm_client = session.client('acm')

    certificate = GetCertificate(session, prefix)

    if certificate is None:
        print(f"Certificate not found. Skipping...")
        return

    print(f"Deleting certificate {certificate['CertificateArn']}")
    arn = certificate['CertificateArn']

    acm_client.delete_certificate(
        CertificateArn=arn
    )

def DeleteCloudFrontOriginAccessIdentity(session, prefix):
    cloudfront_client = session.client('cloudfront')

    oai = GetCloudFrontOriginAccessIdentity(session, prefix)

    if oai is None:
        print(f"CloudFront origin access identity not found. Skipping...")
        return

    oai_id = oai['CloudFrontOriginAccessIdentity']['Id']

    etag = oai['ETag']

    cloudfront_client.delete_cloud_front_origin_access_identity(
        Id=oai_id,
        IfMatch=etag
    )

def DeleteHostedZone(session, prefix):
    route53_client = session.client('route53')

    hosted_zone = GetHostedZone(session, prefix)

    if hosted_zone is None:
        print(f"Hosted zone not found. Skipping...")
        return

    print(f"Deleting hosted zone {hosted_zone['Id']}")
    zone_id = hosted_zone['Id']

    route53_client.delete_hosted_zone(
        Id=zone_id
    )