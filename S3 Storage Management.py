import boto3
import os
from botocore.exceptions import ClientError

# === Configuration ===
region = 'ap-south-1'  
bucket_name = 'my-ccvt-project-bucket'   # Must be globally unique
local_upload_file = r'D:\AutomatedEC2Management\s3file.txt'
local_download_file = r'D:\AutomatedEC2Management\s3files\downloaded_data.txt'
object_key = 'backups/data.txt'

# === Initialize S3 Client & Resource ===
s3_client = boto3.client('s3', region_name=region)
s3_resource = boto3.resource('s3', region_name=region)


def create_bucket(name, region):
    try:
        if region == 'us-east-1':
            s3_client.create_bucket(Bucket=name)
        else:
            s3_client.create_bucket(
                Bucket=name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"✓ Bucket '{name}' created.")
    except ClientError as e:
        code = e.response['Error']['Code']
        if code == 'BucketAlreadyOwnedByYou':
            print(f"✓ Bucket '{name}' already exists and is owned by you.")
        elif code == 'BucketAlreadyExists':
            print(f"✗ Bucket name '{name}' is already taken globally. Choose a different name.")
            exit(1)
        else:
            raise


def enable_versioning(name):
    s3_resource.BucketVersioning(name).enable()
    print(f"✓ Versioning enabled on bucket '{name}'.")


def set_lifecycle_policy(name):
    lifecycle_configuration = {
        'Rules': [
            {
                'ID': 'RetainFor30Days',
                'Prefix': 'backups/',
                'Status': 'Enabled',
                'Expiration': {'Days': 30},
                'NoncurrentVersionExpiration': {'NoncurrentDays': 30}
            }
        ]
    }
    s3_client.put_bucket_lifecycle_configuration(
        Bucket=name,
        LifecycleConfiguration=lifecycle_configuration
    )
    print(f"✓ Lifecycle policy applied to bucket '{name}'.")


def enable_bucket_encryption(name):
    s3_client.put_bucket_encryption(
        Bucket=name,
        ServerSideEncryptionConfiguration={
            'Rules': [{
                'ApplyServerSideEncryptionByDefault': {
                    'SSEAlgorithm': 'AES256'
                }
            }]
        }
    )
    print(f"✓ Server-side encryption enabled on bucket '{name}'.")


def upload_file(name, file_path, key):
    if not os.path.isfile(file_path):
        print(f"✗ Upload failed: local file '{file_path}' not found.")
        return
    try:
        s3_client.upload_file(
            Filename=file_path,
            Bucket=name,
            Key=key,
            ExtraArgs={'ServerSideEncryption': 'AES256'}
        )
        print(f"✓ Uploaded '{file_path}' to 's3://{name}/{key}'.")
    except ClientError as e:
        print("✗ Upload failed:", e)


def download_file(name, key, download_path):
    # ensure target directory exists
    target_dir = os.path.dirname(download_path)
    os.makedirs(target_dir, exist_ok=True)

    try:
        s3_client.download_file(
            Bucket=name,
            Key=key,
            Filename=download_path
        )
        print(f"✓ Downloaded 's3://{name}/{key}' to '{download_path}'.")
    except ClientError as e:
        print("✗ Download failed:", e)


def main():
    create_bucket(bucket_name, region)
    enable_versioning(bucket_name)
    set_lifecycle_policy(bucket_name)
    enable_bucket_encryption(bucket_name)
    upload_file(bucket_name, local_upload_file, object_key)
    download_file(bucket_name, object_key, local_download_file)


if __name__ == '__main__':
    main()
    print("S3 Storage Management completed.")
    print("Exiting...")