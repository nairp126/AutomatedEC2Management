import boto3
import json
import zipfile
import time
import os
from botocore.exceptions import ClientError

# === Configuration ===
region = 'ap-south-1'# Change to your preferred region
role_name = 'EC2CleanupLambdaRole'
lambda_function_name = 'TerminateOldEC2Instances'
zip_path = 'lambda_function.zip'


def create_lambda_zip(zip_filename, source_file):
    with zipfile.ZipFile(zip_filename, 'w') as z:
        z.write(source_file, arcname='lambda_function.py')

if not os.path.isfile('lambda_function.zip') or os.path.getsize('lambda_function.zip') == 0:
    print("❌ Error: lambda_function.zip is missing or empty.")
    exit(1)

# Managed policies your Lambda needs
policies = [
    'arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess',
    'arn:aws:iam::aws:policy/AmazonEC2FullAccess',
    'arn:aws:iam::aws:policy/CloudWatchLogsFullAccess'
]

# Trust policy for Lambda
assume_role_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }
    ]
}

iam = boto3.client('iam', region_name=region)
lambda_client = boto3.client('lambda', region_name=region)

def create_iam_role():
    try:
        print(f"Creating IAM role '{role_name}'...")
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description='Role for Lambda to terminate stopped EC2 instances'
        )
        role_arn = resp['Role']['Arn']
        print("  ✓ Role created:", role_arn)
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"  ! Role '{role_name}' already exists, fetching ARN...")
            role_arn = iam.get_role(RoleName=role_name)['Role']['Arn']
        else:
            print("  ✗ Failed to create role:", e)
            raise
    return role_arn

def attach_policies(role_name):
    for policy in policies:
        try:
            print(f"Attaching policy {policy}...")
            iam.attach_role_policy(RoleName=role_name, PolicyArn=policy)
            print("  ✓ Attached")
        except ClientError as e:
            print(f"  ✗ Failed to attach {policy}:", e)
            raise

def wait_for_role_propagation(role_name):
    # Sometimes IAM role propagation takes a few seconds
    print("Waiting for IAM role propagation...", end='', flush=True)
    time.sleep(10)
    print(" done.")

def deploy_lambda(role_arn):
    # Read in ZIP package
    try:
        with open(zip_path, 'rb') as f:
            zipped_code = f.read()
    except FileNotFoundError:
        print(f"✗ ZIP file '{zip_path}' not found.")
        return

    # Create Lambda
    try:
        print(f"Creating Lambda function '{lambda_function_name}'...")
        response = lambda_client.create_function(
            FunctionName=lambda_function_name,
            Runtime='python3.9',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zipped_code},
            Timeout=60,
            MemorySize=128,
            Publish=True
        )
        print("  ✓ Lambda created. ARN:", response['FunctionArn'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            print(f"  ! Function '{lambda_function_name}' already exists.")
        else:
            print("  ✗ Failed to create Lambda:", e)
            raise

def main():
    # 1) Package the code
    source_py = 'lambda_function.py'
    if os.path.isfile(source_py):
        print(f"Packaging {source_py} into {zip_path}...")
        create_lambda_zip(zip_path, source_py)
        # optional verification
        with zipfile.ZipFile(zip_path, 'r') as z:
            print("  ✓ Zip contains:", z.namelist())
    else:
        print(f"❌ Error: source file '{source_py}' not found.")
        return

    # 2) Validate zip
    if not os.path.isfile(zip_path) or os.path.getsize(zip_path) == 0:
        print("❌ Error: lambda_function.zip is missing or empty.")
        return

    # 3) IAM / Lambda deployment
    try:
        role_arn = create_iam_role()
        attach_policies(role_name)
        wait_for_role_propagation(role_name)
        deploy_lambda(role_arn)
    except Exception as e:
        print("Deployment aborted due to error:", e)


if __name__ == '__main__':
    main()
    print("Deployment completed.")
    print("You can now configure the Lambda function in the AWS Console.")