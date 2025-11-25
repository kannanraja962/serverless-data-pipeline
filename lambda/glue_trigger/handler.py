import json
import boto3
import os
from datetime import datetime

glue_client = boto3.client('glue')
s3_client = boto3.client('s3')
cloudwatch = boto3.client('cloudwatch')

GLUE_JOB_NAME = os.environ.get('GLUE_JOB_NAME', 'etl-sales-data')
DATA_QUALITY_JOB = os.environ.get('DATA_QUALITY_JOB', 'data-quality-check')

def lambda_handler(event, context):
    """
    Orchestrates Glue ETL workflow:
    1. Checks if data quality validation passed
    2. Starts appropriate Glue job
    3. Monitors job status
    4. Publishes metrics to CloudWatch
    """
    
    try:
        # Extract details from event (from previous Lambda or S3)
        if 'Records' in event:
            # Triggered by S3
            bucket = event['Records'][0]['s3']['bucket']['name']
            key = event['Records'][0]['s3']['object']['key']
        else:
            # Triggered by another Lambda
            bucket = event['bucket']
            key = event['key']
        
        print(f"Triggering Glue job for: s3://{bucket}/{key}")
        
        # Check metadata for data quality status
        metadata_key = key.replace('raw/', 'metadata/').replace('.csv', '_metadata.json')
        
        try:
            metadata_obj = s3_client.get_object(Bucket=bucket, Key=metadata_key)
            metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))
            validation_status = metadata.get('validation_status', 'UNKNOWN')
            total_rows = metadata.get('stats', {}).get('total_rows', 0)
        except:
            print("No metadata found, proceeding with default validation")
            validation_status = 'UNKNOWN'
            total_rows = 0
        
        print(f"Validation status: {validation_status}, Total rows: {total_rows}")
        
        # Determine which Glue job to run
        if validation_status == 'PASSED' or validation_status == 'UNKNOWN':
            job_name = GLUE_JOB_NAME
            print(f"Starting main ETL job: {job_name}")
        else:
            job_name = DATA_QUALITY_JOB
            print(f"Data quality issues detected, starting quality check job: {job_name}")
        
        # Determine DPU allocation based on file size
        file_size_mb = get_file_size_mb(bucket, key)
        dpu_allocation = calculate_dpu(file_size_mb, total_rows)
        
        # Start Glue job with dynamic parameters
        job_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        response = glue_client.start_job_run(
            JobName=job_name,
            Arguments={
                '--S3_INPUT_PATH': f's3://{bucket}/{key}',
                '--S3_OUTPUT_PATH': f's3://{bucket}/processed/',
                '--REDSHIFT_TABLE': 'sales_fact',
                '--JOB_RUN_ID': job_run_id,
                '--VALIDATION_STATUS': validation_status,
                '--TOTAL_ROWS': str(total_rows)
            },
            MaxCapacity=dpu_allocation  # Dynamic DPU allocation
        )
        
        glue_job_run_id = response['JobRunId']
        print(f"Glue job started: {glue_job_run_id}")
        
        # Publish metrics to CloudWatch
        publish_metrics(job_name, file_size_mb, total_rows)
        
        # Store job metadata
        job_metadata = {
            'glue_job_name': job_name,
            'glue_job_run_id': glue_job_run_id,
            'input_file': key,
            'file_size_mb': file_size_mb,
            'total_rows': total_rows,
            'dpu_allocated': dpu_allocation,
            'triggered_at': datetime.now().isoformat(),
            'validation_status': validation_status
        }
        
        # Save job tracking info
        tracking_key = f"job_tracking/{job_run_id}.json"
        s3_client.put_object(
            Bucket=bucket,
            Key=tracking_key,
            Body=json.dumps(job_metadata, indent=2),
            ContentType='application/json'
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Glue job triggered successfully',
                'job_name': job_name,
                'job_run_id': glue_job_run_id,
                'input_file': key,
                'dpu_allocated': dpu_allocation,
                'metadata': job_metadata
            })
        }
        
    except Exception as e:
        print(f"Error triggering Glue job: {str(e)}")
        
        # Send error notification (optional)
        # sns_client.publish(...)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'input_file': key
            })
        }


def get_file_size_mb(bucket, key):
    """Get file size in MB"""
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        size_bytes = response['ContentLength']
        return round(size_bytes / (1024 * 1024), 2)
    except:
        return 0


def calculate_dpu(file_size_mb, total_rows):
    """
    Calculate optimal DPU allocation based on file size and row count
    DPU = Data Processing Unit (Glue compute capacity)
    """
    # Base allocation
    if file_size_mb < 10 or total_rows < 10000:
        return 2  # Minimum DPU
    elif file_size_mb < 100 or total_rows < 100000:
        return 5
    elif file_size_mb < 500 or total_rows < 1000000:
        return 10
    else:
        return 20  # Large files


def publish_metrics(job_name, file_size_mb, total_rows):
    """Publish custom metrics to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace='DataPipeline/Glue',
            MetricData=[
                {
                    'MetricName': 'FileSizeProcessed',
                    'Value': file_size_mb,
                    'Unit': 'None',
                    'Dimensions': [
                        {'Name': 'JobName', 'Value': job_name}
                    ]
                },
                {
                    'MetricName': 'RowsProcessed',
                    'Value': total_rows,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'JobName', 'Value': job_name}
                    ]
                }
            ]
        )
        print("Metrics published to CloudWatch")
    except Exception as e:
        print(f"Error publishing metrics: {str(e)}")
