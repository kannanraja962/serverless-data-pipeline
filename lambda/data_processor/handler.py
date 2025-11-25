import json
import boto3
import pandas as pd
from io import StringIO
from datetime import datetime

s3_client = boto3.client('s3')
sns_client = boto3.client('sns')

def lambda_handler(event, context):
    """
    Validates and preprocesses data before Glue ETL
    - Checks file format and structure
    - Validates data quality
    - Sends notifications if issues found
    """
    
    try:
        # Extract S3 details from event
        bucket = event['bucket']
        key = event['key']
        
        print(f"Processing file: s3://{bucket}/{key}")
        
        # Download file from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read().decode('utf-8')
        
        # Read CSV into DataFrame
        df = pd.read_csv(StringIO(file_content))
        
        # Data Quality Checks
        validation_results = {
            'total_rows': len(df),
            'null_values': df.isnull().sum().to_dict(),
            'duplicate_orders': df.duplicated(subset=['order_id']).sum(),
            'invalid_amounts': (df['sales_amount'] <= 0).sum() if 'sales_amount' in df.columns else 0,
            'date_range': {
                'min': str(df['order_date'].min()) if 'order_date' in df.columns else None,
                'max': str(df['order_date'].max()) if 'order_date' in df.columns else None
            }
        }
        
        print(f"Validation results: {json.dumps(validation_results, indent=2)}")
        
        # Check if data passes quality thresholds
        issues = []
        if validation_results['duplicate_orders'] > 0:
            issues.append(f"Found {validation_results['duplicate_orders']} duplicate orders")
        
        if validation_results['invalid_amounts'] > 0:
            issues.append(f"Found {validation_results['invalid_amounts']} invalid amounts")
        
        # Add metadata
        metadata = {
            'processed_by': 'data_processor_lambda',
            'processed_at': datetime.now().isoformat(),
            'file_name': key,
            'validation_status': 'PASSED' if not issues else 'WARNING',
            'issues': issues,
            'stats': validation_results
        }
        
        # Save metadata to S3
        metadata_key = key.replace('raw/', 'metadata/').replace('.csv', '_metadata.json')
        s3_client.put_object(
            Bucket=bucket,
            Key=metadata_key,
            Body=json.dumps(metadata, indent=2),
            ContentType='application/json'
        )
        
        # If critical issues found, send SNS notification
        if issues:
            print(f"Data quality issues found: {issues}")
            # Uncomment to send SNS notification
            # sns_client.publish(
            #     TopicArn='arn:aws:sns:region:account:data-quality-alerts',
            #     Subject='Data Quality Warning',
            #     Message=f"Issues in {key}:\n" + "\n".join(issues)
            # )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data processing completed',
                'validation_status': metadata['validation_status'],
                'file': key,
                'metadata': metadata
            })
        }
        
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'file': key
            })
        }
