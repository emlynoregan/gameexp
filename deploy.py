import botocore
import traceback
import argparse

from deploy_shared import AddQueueEventSourceMapping, CalculateQueueUrl, CreateOrUpdateCloudFrontDistribution, \
    CreateOrUpdateCloudFrontOriginAccessIdentity, CreateOrUpdateCustomPolicy, CreateOrUpdateDynamoDBTable, CreateOrUpdateHostedZone, \
    CreateOrUpdateLambda, CreateOrUpdateLayer, CreateOrUpdateRole, CreateOrUpdateRoute53ResourceRecords, \
    CreateOrUpdateS3Bucket, CreateOrUpdateSQSQueue, DeleteCertificate, DeleteCloudFrontDistribution, \
    DeleteCloudFrontOriginAccessIdentity, DeleteCustomPolicy, DeleteDynamoDBTable, DeleteEventSourceMappings, \
    DeleteHostedZone, DeleteLambda, DeleteLayer, DeleteQueue, DeleteRole, DeleteS3Bucket, GetCertificate, \
    GetCloudFrontOriginAccessIdentity, GetRoleArn, get_aws_credentials, get_bucket_name, get_lambda_role_name, \
    get_lambda_role_description, get_queue_name, get_lambda_function_name, get_lambda_function_description, \
    get_table_name, get_secret_name, get_policy_name, get_full_bucket_name, \
    get_session, get_credentials, \
    GetConfigValue, get_background_lambda_function_name, \
    get_background_lambda_function_description, get_layer_name, get_layer_description

###################################################################
###################################################################
#
# Create infrastructure
#
###################################################################
###################################################################

def CreateInfrastructure(session, credentials, prefix=None):
    print("Creating infrastructure...")

    print ("* Create the queue")
    CreateOrUpdateSQSQueue(session, get_queue_name(prefix))

    print ("* Create the Dynamo DB table")
    CreateOrUpdateDynamoDBTable(session, get_table_name(prefix))

    print ("* Create the cloudfront origin access identity")
    CreateOrUpdateCloudFrontOriginAccessIdentity(session, prefix)
    
    print ("* Create the S3 bucket")
    CreateOrUpdateS3Bucket(session, prefix, get_bucket_name(session, prefix))

    print ("* Create custom policy for lambda")
    CreateOrUpdateCustomPolicy(session, get_policy_name(prefix), get_table_name(prefix), get_queue_name(prefix), get_secret_name(prefix), get_bucket_name(session, prefix))

    print ("* Create a role for lambda to use")
    role_arn = CreateOrUpdateRole(session, get_lambda_role_name(prefix), get_lambda_role_description(prefix), get_policy_name(prefix))

    print ("* Create the lambda layer")
    CreateOrUpdateLayer(session, get_layer_name(prefix), get_layer_description(prefix), "lambda_layer")

    print ("* Create the lambda function")
    CreateOrUpdateLambda(
        session, 
        get_lambda_function_name(prefix), get_lambda_function_description(prefix), 
        "lambda",
        role_arn, "lambda_handler.handler", 
        {
            # "GOOGLE_CLIENT_ID": GetConfigValue(prefix, "google_client_id"),
            "bucket_name": get_bucket_name(session, prefix),
            "table_name": get_table_name(prefix),
            "queue_name": get_queue_name(prefix),
            "queue_url": CalculateQueueUrl(session, get_queue_name(prefix)),
            "domain_name": GetConfigValue(prefix, "domain_name"),
            "openai_api_key": credentials["openai_api_key"]
        },
        get_layer_name(prefix)
    )

    print ("* Create the background lambda function")
    CreateOrUpdateLambda(
        session, 
        get_background_lambda_function_name(prefix), get_background_lambda_function_description(prefix), 
        "blambda",
        role_arn, "lambda_handler.lambda_handler", 
        {
            # "GOOGLE_CLIENT_ID": GetConfigValue(prefix, "google_client_id"),
            "bucket_name": get_bucket_name(session, prefix),
            "table_name": get_table_name(prefix),
            "domain_name": GetConfigValue(prefix, "domain_name"),
            "queue_name": get_queue_name(prefix),
            "queue_url": CalculateQueueUrl(session, get_queue_name(prefix)),
            "openai_api_key": credentials["openai_api_key"]
        },
        get_layer_name(prefix)
    )

    print ("* Create the event source mapping")
    AddQueueEventSourceMapping(session, get_queue_name(prefix), get_background_lambda_function_name(prefix))

    print ("* Create a Certificate")
    certificate = GetCertificate(session, prefix)

    if not certificate:
        raise Exception("Certificate not found")

    oai = GetCloudFrontOriginAccessIdentity(session, prefix)

    # oai_canonical_user_id = oai['CloudFrontOriginAccessIdentity']['S3CanonicalUserId']
    oai_id = oai['CloudFrontOriginAccessIdentity']['Id']

    print ("* Create a CloudFront distribution")
    domain_name = GetConfigValue(prefix, 'domain_name')
    CreateOrUpdateCloudFrontDistribution(session, prefix, get_full_bucket_name(session, prefix), domain_name, oai_id)

    print ("* Create a Route53 Hosted Zone")
    CreateOrUpdateHostedZone(session, prefix)

    print ("* Create Route53 Resource Records")
    CreateOrUpdateRoute53ResourceRecords(session, prefix)

    print("Done.")

    # now print clickable links to the lambdas in the console
    def print_lambda_link(function_name):
        region = session.region_name
        console_url = f"https://{region}.console.aws.amazon.com/lambda/home?region={region}#/functions/{function_name}"
        print (f"Lambda {function_name} in AWS Console: {console_url}")

    function_name = get_lambda_function_name(prefix)
    print_lambda_link(function_name)

    function_name = get_background_lambda_function_name(prefix)
    print_lambda_link(function_name)

def DeployCode(session, credentials, prefix=None):
    print("Deploying code...")

    role_arn = GetRoleArn(session, get_lambda_role_name(prefix))

    print ("* Create the lambda layer")
    CreateOrUpdateLayer(session, get_layer_name(prefix), get_layer_description(prefix), "lambda_layer")

    print ("* Create the lambda function")
    CreateOrUpdateLambda(
        session, 
        get_lambda_function_name(prefix), get_lambda_function_description(prefix), 
        "lambda",
        role_arn, "lambda_handler.handler", 
        {
            # "GOOGLE_CLIENT_ID": GetConfigValue(prefix, "google_client_id"),
            "bucket_name": get_bucket_name(session, prefix),
            "table_name": get_table_name(prefix),
            "queue_name": get_queue_name(prefix),
            "queue_url": CalculateQueueUrl(session, get_queue_name(prefix)),
            "domain_name": GetConfigValue(prefix, "domain_name"),
            "openai_api_key": credentials["openai_api_key"]
        },
        get_layer_name(prefix)
    )

    print ("* Create the background lambda function")
    CreateOrUpdateLambda(
        session, 
        get_background_lambda_function_name(prefix), get_background_lambda_function_description(prefix), 
        "blambda",
        role_arn, "lambda_handler.lambda_handler", 
        {
            # "GOOGLE_CLIENT_ID": GetConfigValue(prefix, "google_client_id"),
            "bucket_name": get_bucket_name(session, prefix),
            "table_name": get_table_name(prefix),
            "domain_name": GetConfigValue(prefix, "domain_name"),
            "queue_name": get_queue_name(prefix),
            "queue_url": CalculateQueueUrl(session, get_queue_name(prefix)),
            "openai_api_key": credentials["openai_api_key"]
        },
        get_layer_name(prefix)
    )

    # now print clickable links to the lambdas in the console
    def print_lambda_link(function_name):
        region = session.region_name
        console_url = f"https://{region}.console.aws.amazon.com/lambda/home?region={region}#/functions/{function_name}"
        print (f"Lambda {function_name} in AWS Console: {console_url}")

    function_name = get_lambda_function_name(prefix)
    print_lambda_link(function_name)

    function_name = get_background_lambda_function_name(prefix)
    print_lambda_link(function_name)


###################################################################
###################################################################
#
# Delete infrastructure
#
###################################################################
###################################################################

def DestroyInfrastructure(session, prefix, delete_data, delete_certificate, delete_zone):
    print("Destroying infrastructure...")

    print("* Deleting the lambda...")
    DeleteLambda(session, get_lambda_function_name(prefix))

    print("* Deleting the background lambda...")
    DeleteLambda(session, get_background_lambda_function_name(prefix))

    print ("* Deleting the lambda layer...")
    DeleteLayer(session, get_layer_name(prefix))

    print("* Deleting the lambda role...")
    DeleteRole(session, get_lambda_role_name(prefix))

    print("* Delete Policy")
    DeleteCustomPolicy(session, prefix)

    if delete_data:
        print ("* Delete the Dynamo DB table")
        DeleteDynamoDBTable(session, get_table_name(prefix))

        print ("* Delete the S3 bucket")
        DeleteS3Bucket(session, get_bucket_name(session, prefix))

    if delete_certificate:
        print("* Delete Certificate")
        DeleteCertificate(session, prefix)

    if delete_zone:
        print("* Delete Hosted Zone")
        DeleteHostedZone(session, prefix)

    print ("* Delete the CloudFront distribution")
    full_bucket_name = get_full_bucket_name(session, prefix)
    DeleteCloudFrontDistribution(session, prefix, full_bucket_name)

    print ("* Delete the CloudFront origin access identity")
    DeleteCloudFrontOriginAccessIdentity(session, prefix)

    print ("* Delete all Event Source Mappings from the lambda")
    DeleteEventSourceMappings(session, get_lambda_function_name(prefix))

    print ("* Delete all Event Source Mappings from the background lambda")
    DeleteEventSourceMappings(session, get_background_lambda_function_name(prefix))

    print ("* Delete the queue")
    DeleteQueue(session, get_queue_name(prefix))

    print("done")

def main():
    # usage: python deploy.py <prefix> [--destroy] [--delete-data] [--delete-cert] [--delete-zone] [--code-only]

    # use argparse to parse the command line arguments
    parser = argparse.ArgumentParser(description='Deploy the infrastructure.')

    parser.add_argument('prefix', help='The prefix to use for the infrastructure.')
    parser.add_argument('--destroy', action='store_true', help='Destroy the infrastructure.')
    parser.add_argument('--delete-data', action='store_true', help='Delete the data.')
    parser.add_argument('--delete-cert', action='store_true', help='Delete the certificate.')
    parser.add_argument('--delete-zone', action='store_true', help='Delete the zone.')
    parser.add_argument('--code-only', action='store_true', help='Only deploy the code.')

    args = parser.parse_args()

    prefix = args.prefix
    destroy = args.destroy
    delete_data = args.delete_data
    delete_cert = args.delete_cert
    delete_zone = args.delete_zone
    code_only = args.code_only

    try:
        credentials = get_credentials()
        aws_credentials = get_aws_credentials()
        my_session = get_session(aws_credentials)

        # check if the --destroy flag is set
        if destroy:
            # destroy the infrastructure
            DestroyInfrastructure(my_session, prefix, delete_data, delete_cert, delete_zone)
        else:
            # create the infrastructure
            if code_only:
                DeployCode(my_session, credentials, prefix)
            else:
                CreateInfrastructure(my_session, credentials, prefix)

    except FileNotFoundError as e:
        print("Can't find the credentials.json file.\nCopy the credentials_template.json file and rename it to credentials.json, then fill in your own AWS credentials.")
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'UnrecognizedClientException':
            print("Bad AWS security token.\nMake sure you have the correct AWS credentials in the credentials.json file.")
        else:
            # print the traceback
            print(traceback.format_exc())
    except Exception as e:
        # print the traceback
        print(traceback.format_exc())

# standard calling of main function
if __name__ == "__main__":
    main()