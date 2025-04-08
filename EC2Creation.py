import boto3
import time

# Set the AWS Region (modify as needed)
region = 'ap-south-1'

# Initialize EC2 resource and client
ec2_resource = boto3.resource('ec2', region_name=region)
ec2_client = boto3.client('ec2', region_name=region)

# Initialize IAM client
iam_client = boto3.client('iam')

# -----------------------------
# 0. Create IAM Instance Profile (if not exists)
# -----------------------------
# Specify the IAM role and instance profile names.
role_name = 'EC2_Lambda_S3_Role'       # Your IAM role created previously
instance_profile_name = 'EC2_Instance_Profile'  # Name for the instance profile

# Check if the instance profile exists
try:
    iam_client.get_instance_profile(InstanceProfileName=instance_profile_name)
    print(f"Instance profile '{instance_profile_name}' already exists.")
except iam_client.exceptions.NoSuchEntityException:
    print(f"Instance profile '{instance_profile_name}' not found. Creating instance profile...")
    # Create the instance profile
    iam_client.create_instance_profile(InstanceProfileName=instance_profile_name)
    # Adding a short delay to allow the new instance profile to propagate
    time.sleep(10)
    # Attach the role to the instance profile
    iam_client.add_role_to_instance_profile(
        InstanceProfileName=instance_profile_name,
        RoleName=role_name
    )
    print(f"Instance profile '{instance_profile_name}' created and role '{role_name}' added.")

# -----------------------------
# 1. Launch an EC2 Instance
# -----------------------------
print("Launching EC2 instance...")

# Replace with a valid AMI ID for your region and your key pair name
ami_id = 'ami-002f6e91abff6eb96'  # Example AMI ID, change it to a valid one
instance_type = 't2.micro'
key_name = 'AutomatedEC2'         # Replace with your actual key pair name

try:
    instances = ec2_resource.create_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        KeyName=key_name,
        IamInstanceProfile={'Name': instance_profile_name}
    )
    instance = instances[0]
    print("Instance created. Waiting for it to enter the 'running' state...")
    instance.wait_until_running()
    instance.reload()  # Refresh instance attributes
    print(f"Instance is now running. Instance ID: {instance.id}")
except Exception as e:
    print("Error launching EC2 instance:", e)
    exit(1)

# -----------------------------
# 2. Create and Attach an EBS Volume
# -----------------------------
print("\nCreating an EBS volume...")
try:
    # Create an 8 GB volume in the same availability zone as the instance
    volume = ec2_resource.create_volume(
        AvailabilityZone=instance.placement['AvailabilityZone'],
        Size=8,  # Size in GB
        VolumeType='gp2'
    )
    print("Volume created. Waiting for it to become available...")
    ec2_client.get_waiter('volume_available').wait(VolumeIds=[volume.id])
    print(f"Volume is now available. Volume ID: {volume.id}")
    print("Attaching volume to instance...")
    ec2_client.attach_volume(
        VolumeId=volume.id,
        InstanceId=instance.id,
        Device='/dev/sdf'
    )
    print(f"Volume {volume.id} attached to instance {instance.id}.")
except Exception as e:
    print("Error creating or attaching EBS volume:", e)

# -----------------------------
# 3. Automatic Backup via Snapshot
# -----------------------------
print("\nCreating a snapshot for backup...")
try:
    snapshot = volume.create_snapshot(Description=f"Backup snapshot for volume {volume.id}")
    print(f"Snapshot {snapshot.id} initiated for volume {volume.id}.")
except Exception as e:
    print("Error creating snapshot:", e)

# -----------------------------
# 4. CloudWatch Monitoring (Optional)
# -----------------------------
print("\nSetting up a CloudWatch alarm for CPU utilization...")
cloudwatch_client = boto3.client('cloudwatch', region_name=region)

try:
    alarm_response = cloudwatch_client.put_metric_alarm(
        AlarmName='HighCPUUtilization',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=1,
        MetricName='CPUUtilization',
        Namespace='AWS/EC2',
        Period=300,
        Statistic='Average',
        Threshold=70.0,
        ActionsEnabled=False,  # Set to True if you want actions to be triggered
        AlarmDescription='Alarm when server CPU exceeds 70%',
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': instance.id
            },
        ],
    )
    print("CloudWatch alarm 'HighCPUUtilization' created.")
except Exception as e:
    print("Error creating CloudWatch alarm:", e)
