import json
import boto3
import os
from datetime import datetime

glue_client = boto3.client('glue')
s3_client = boto3.client('s3')

GLUE_JOB_NAME = os.environ.get('GLUE_JOB_NAME', 'etl-sales-data')

def lambda_handler(event, context):
    """
    Triggered when new file uploaded to S3
    Starts Glue ETL job to process the data
    """
    
    print(f"Event received: {json.dumps(event)}")
    
    # Extract S3 bucket and key from event
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        file_size = record['s3']['object']['size']
        
        print(f"New file detected: s3://{bucket}/{key} ({file_size} bytes)")
        
        # Validate file type
        if not key.endswith(('.csv', '.json', '.parquet')):
            print(f"Skipping unsupported file type: {key}")
            continue
        
        # Start Glue job
        try:
            response = glue_client.start_job_run(
                JobName=GLUE_JOB_NAME,
                Arguments={
                    '--S3_INPUT_PATH': f's3://{bucket}/{key}',
                    '--S3_OUTPUT_PATH': f's3://{bucket}/processed/',
                    '--REDSHIFT_TABLE': 'sales_fact',
                    '--JOB_RUN_ID': datetime.now().strftime('%Y%m%d_%H%M%S')
                }
            )
            
            job_run_id = response['JobRunId']
            print(f"Glue job started successfully: {job_run_id}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Pipeline triggered successfully',
                    'glue_job_run_id': job_run_id,
                    'input_file': key
                })
            }
            
        except Exception as e:
            print(f"Error starting Glue job: {str(e)}")
            raise
    
    return {
        'statusCode': 200,
        'body': json.dumps('No valid files to process')
    }
