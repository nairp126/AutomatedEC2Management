import boto3
import json

# Initialize the IAM client
iam_client = boto3.client('iam')

# Define the role name
role_name = 'EC2_Lambda_S3_Role22'

# Trust policy for EC2 and Lambda services
assume_role_policy_document = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "ec2.amazonaws.com",
                    "lambda.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
})

# Create the IAM role with the defined trust policy
try:
    create_role_response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=assume_role_policy_document,
        Description='Role for managing EC2, Lambda, and S3 operations.'
    )
    print("IAM Role created successfully:", create_role_response['Role']['Arn'])
except iam_client.exceptions.EntityAlreadyExistsException:
    print("Role already exists. Continuing with policy attachment.")
except Exception as e:
    print("Error creating role:", e)

# List of policies to attach to the role
policies = [
    'arn:aws:iam::aws:policy/AmazonEC2FullAccess',
    'arn:aws:iam::aws:policy/AWSLambda_FullAccess',
    'arn:aws:iam::aws:policy/AmazonS3FullAccess'
]

# Attach each policy to the role
for policy_arn in policies:
    try:
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )
        print(f"Attached policy: {policy_arn}")
    except Exception as e:
        print(f"Error attaching policy {policy_arn}:", e)
