from deploy_shared import get_bucket_name, get_aws_credentials, get_session, GetConfigValue, \
    get_lambda_function_name
import sys
import os
import boto3
import shutil
import argparse

def main():
    """
    We're deploying the react ui to AWS.

    It's in the "./spelunk-ui" folder.
    We need to build it using npm run build first.

    Then, we need to upload it to S3.

    usage: python deploy_ui.py <prefix>

    """
    credentials = get_aws_credentials()
    session = get_session(credentials)

    # get the prefix from the command line arguments using argparse
    parser = argparse.ArgumentParser()

    # note that prefix is required
    parser.add_argument("prefix", help="The prefix to use for the deployment", type=str)

    args = parser.parse_args()

    prefix = args.prefix

    domain_name = GetConfigValue(prefix, "domain_name")

    # get the bucket name
    bucket_name = get_bucket_name(session, prefix)
    print ("bucket_name: " + bucket_name)

    # get the lambda function url (that's our api endpoint)
    lambda_name = get_lambda_function_name(prefix)

    lambda_client = session.client('lambda')

    function_url_config = lambda_client.get_function_url_config(FunctionName=lambda_name)

    function_url = function_url_config['FunctionUrl']
    print ("function_url: " + function_url)

    # # get the auth0 config
    # auth0 = GetConfigValue(prefix, "auth0")

    app_name = GetConfigValue(prefix, "app_name")

    # print (f"auth0: {auth0}")

    # get the google client id
    # google_client_id = GetConfigValue(prefix, "google_client_id")

    # here, create the .env file in the ui folder

    with open('./spelunk-ui/.env.template', 'r') as f:
        env = f.read()

    env = env.replace('**app_name**', app_name)
    env = env.replace('**api_url**', function_url)
    # env = env.replace('**auth0_domain**', auth0.get('domain'))
    # env = env.replace('**auth0_client_id**', auth0.get('client_id'))

    with open('./spelunk-ui/.env', 'w') as f:
        f.write(env)

    # change working directory to the ui folder
    os.chdir('./spelunk-ui')

    # build the react ui, stop if it fails
    print("Building react ui...")
    result = os.system(f"npm run build")# {domain_name} {function_url}") # {google_client_id}")
    if result != 0:
        print("Build failed.")
        sys.exit(1)

    # # change working directory back to the root
    # os.chdir('..')

    # now upload all files in the ./build-dist folder to S3, to the path "ui"
    # we're using the boto3 library to do this.

    print("Uploading files to S3...")
    s3_client = session.client('s3')
    # change working directory to the build folder
    os.chdir('./build')

    lastbuild_path = f'../lastbuild/{prefix}'

    if not os.path.exists(lastbuild_path):
        os.mkdir(lastbuild_path)

    for root, dirs, files in os.walk('.'):
        for file in files:
            # first, try to open the same file from ../lastbuild, and compare it to the current file.
            # if they're the same, we don't need to upload it.

            new_file_path = os.path.abspath(os.path.join(root, file))
            print(f"new_file_path: {new_file_path}")
            lastbuild_file_path = os.path.abspath(os.path.join('..', 'lastbuild', prefix, root, file))
            print(f"lastbuild_file_path: {lastbuild_file_path}")

            # get the new file's content
            new_file_content = open(new_file_path, 'rb').read()

            # # check if the file exists in ../lastbuild
            # lastbuild_file_path = lastbuild_file_path

            if os.path.exists(lastbuild_file_path):
                # get the lastbuild file's content
                lastbuild_file_content = open(lastbuild_file_path, 'rb').read()

                # compare the two files
                if new_file_content == lastbuild_file_content:
                    print(f"{file} is the same as last build. Skipping...")
                    continue
            
            # if the file is "index.html", set max-age to 0, also set content-type to text/html
            print(f"Uploading {root}, {dir}, {file}")
            if file == 'index.html' or file == 'scappx.js':
                extra_args = {'CacheControl': 'max-age=0', 'ContentType': 'text/html'}
            # else if the file is javascript, set the content type to application/javascript
            elif file.endswith('.js'):
                extra_args = {'ContentType': 'application/javascript'}
            # else if the file is css, set the content type to text/css
            elif file.endswith('.css'):
                extra_args = {'ContentType': 'text/css'}
            # else if the file is html, set the content type to text/html
            elif file.endswith('.html'):
                extra_args = {'ContentType': 'text/html'}
            elif file.endswith('.png'):
                extra_args = {'ContentType': 'image/png'}
            elif file.endswith('.jpg'):
                extra_args = {'ContentType': 'image/jpg'}
            else:
                extra_args = {}

            s3_key = os.path.join('ui', root, file)
            # normalize the s3 key
            s3_key = os.path.normpath(s3_key)

            # replace backslashes with forward slashes (for windows)
            s3_key = s3_key.replace('\\', '/')

            print (f"s3 key: {s3_key}")
            s3_client.upload_file(os.path.join(root, file), bucket_name, s3_key, ExtraArgs=extra_args)

            # copy the new file to ../lastbuild

            os.makedirs(os.path.dirname(lastbuild_file_path), exist_ok=True)            
            shutil.copyfile (new_file_path, lastbuild_file_path)

    
    print("Done!")


    


# standard calling of main function
if __name__ == "__main__":
    main()