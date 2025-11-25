#!/bin/bash

GLUE_JOB_NAME="etl-sales-data"
S3_BUCKET="your-bucket-name"
TEST_FILE="sample_sales_data.csv"

echo "========================================="
echo "Testing Glue ETL Job"
echo "========================================="

# Upload test data
echo "Uploading test data..."
aws s3 cp ../../data/raw/${TEST_FILE} s3://${S3_BUCKET}/raw/${TEST_FILE}

# Start job run
echo "Starting Glue job..."
JOB_RUN_ID=$(aws glue start-job-run \
    --job-name ${GLUE_JOB_NAME} \
    --arguments "{
        \"--S3_INPUT_PATH\":\"s3://${S3_BUCKET}/raw/${TEST_FILE}\",
        \"--S3_OUTPUT_PATH\":\"s3://${S3_BUCKET}/processed/\",
        \"--REDSHIFT_TABLE\":\"sales_fact\",
        \"--JOB_RUN_ID\":\"test_$(date +%Y%m%d_%H%M%S)\"
    }" \
    --query 'JobRunId' \
    --output text)

echo "Job Run ID: ${JOB_RUN_ID}"
echo ""
echo "Monitor job status with:"
echo "aws glue get-job-run --job-name ${GLUE_JOB_NAME} --run-id ${JOB_RUN_ID}"
echo ""
echo "Or check the Glue console:"
echo "https://console.aws.amazon.com/glue/home#etl:tab=jobs"

# Monitor job (optional)
read -p "Do you want to monitor the job status? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Monitoring job status (checking every 30 seconds)..."
    
    while true; do
        STATUS=$(aws glue get-job-run \
            --job-name ${GLUE_JOB_NAME} \
            --run-id ${JOB_RUN_ID} \
            --query 'JobRun.JobRunState' \
            --output text)
        
        echo "Current status: ${STATUS}"
        
        if [[ "$STATUS" == "SUCCEEDED" ]]; then
            echo "✓ Job completed successfully!"
            break
        elif [[ "$STATUS" == "FAILED" ]] || [[ "$STATUS" == "STOPPED" ]]; then
            echo "✗ Job failed or was stopped"
            
            # Get error message
            aws glue get-job-run \
                --job-name ${GLUE_JOB_NAME} \
                --run-id ${JOB_RUN_ID} \
                --query 'JobRun.ErrorMessage' \
                --output text
            break
        fi
        
        sleep 30
    done
fi
