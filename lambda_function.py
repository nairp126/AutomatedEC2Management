# lambda_function.py
import boto3
from datetime import datetime, timezone, timedelta

ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    response = ec2.describe_instances(Filters=[
        {'Name': 'instance-state-name', 'Values': ['stopped']}
    ])
    return { 'statusCode': 200, 'body': 'OK' }

    stopped_instances = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            state_transition_time = instance.get('StateTransitionReason', '')

            if 'User initiated' in state_transition_time:
                try:
                    timestamp_str = state_transition_time.split('(')[1].replace(' GMT)', '')
                    stopped_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    stopped_time = stopped_time.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)

                    if (now - stopped_time) > timedelta(hours=24):
                        stopped_instances.append(instance_id)

                except Exception as e:
                    print(f"Date parse error for {instance_id}: {e}")
    
    if stopped_instances:
        print(f"Terminating: {stopped_instances}")
        ec2.terminate_instances(InstanceIds=stopped_instances)
        return {"terminated": stopped_instances}
    else:
        return {"message": "No stale instances"}
