#!/bin/bash

# Configuration
GLUE_JOB_NAME="etl-sales-data"
GLUE_ROLE_ARN="arn:aws:iam::YOUR_ACCOUNT_ID:role/GlueServiceRole"
S3_SCRIPT_LOCATION="s3://your-bucket-name/scripts/"
GLUE_VERSION="3.0"
WORKER_TYPE="G.1X"
NUMBER_OF_WORKERS=2

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Deploying Glue ETL Job${NC}"
echo -e "${YELLOW}========================================${NC}"

# Step 1: Upload ETL script to S3
echo -e "\n${GREEN}Step 1: Uploading ETL script to S3...${NC}"
aws s3 cp ../jobs/etl_job.py ${S3_SCRIPT_LOCATION}etl_job.py
aws s3 cp ../jobs/data_quality_check.py ${S3_SCRIPT_LOCATION}data_quality_check.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Scripts uploaded successfully${NC}"
else
    echo -e "${RED}✗ Script upload failed${NC}"
    exit 1
fi

# Step 2: Create or update Glue job
echo -e "\n${GREEN}Step 2: Creating/Updating Glue job...${NC}"

# Check if job exists
JOB_EXISTS=$(aws glue get-job --job-name ${GLUE_JOB_NAME} 2>&1)

if [[ $JOB_EXISTS == *"EntityNotFoundException"* ]]; then
    echo "Job does not exist. Creating new job..."
    
    aws glue create-job \
        --name ${GLUE_JOB_NAME} \
        --role ${GLUE_ROLE_ARN} \
        --command "Name=glueetl,ScriptLocation=${S3_SCRIPT_LOCATION}etl_job.py,PythonVersion=3" \
        --default-arguments '{
            "--TempDir":"s3://your-bucket-name/temp/",
            "--job-language":"python",
            "--enable-metrics":"true",
            "--enable-continuous-cloudwatch-log":"true",
            "--enable-spark-ui":"true",
            "--spark-event-logs-path":"s3://your-bucket-name/spark-logs/"
        }' \
        --glue-version ${GLUE_VERSION} \
        --worker-type ${WORKER_TYPE} \
        --number-of-workers ${NUMBER_OF_WORKERS} \
        --max-retries 1 \
        --timeout 60
    
    echo -e "${GREEN}✓ Glue job created successfully${NC}"
else
    echo "Job exists. Updating job..."
    
    aws glue update-job \
        --job-name ${GLUE_JOB_NAME} \
        --job-update "Role=${GLUE_ROLE_ARN},Command={Name=glueetl,ScriptLocation=${S3_SCRIPT_LOCATION}etl_job.py,PythonVersion=3},GlueVersion=${GLUE_VERSION},WorkerType=${WORKER_TYPE},NumberOfWorkers=${NUMBER_OF_WORKERS}"
    
    echo -e "${GREEN}✓ Glue job updated successfully${NC}"
fi

# Step 3: Create data quality check job
echo -e "\n${GREEN}Step 3: Creating data quality check job...${NC}"

DATA_QUALITY_JOB="data-quality-check"

aws glue create-job \
    --name ${DATA_QUALITY_JOB} \
    --role ${GLUE_ROLE_ARN} \
    --command "Name=glueetl,ScriptLocation=${S3_SCRIPT_LOCATION}data_quality_check.py,PythonVersion=3" \
    --default-arguments '{
        "--TempDir":"s3://your-bucket-name/temp/",
        "--job-language":"python"
    }' \
    --glue-version ${GLUE_VERSION} \
    --worker-type "G.1X" \
    --number-of-workers 2 \
    --max-retries 0 \
    --timeout 30 \
    2>/dev/null || aws glue update-job --job-name ${DATA_QUALITY_JOB} \
    --job-update "Command={ScriptLocation=${S3_SCRIPT_LOCATION}data_quality_check.py}"

echo -e "${GREEN}✓ Data quality job created/updated${NC}"

# Step 4: List all Glue jobs
echo -e "\n${GREEN}Step 4: Listing Glue jobs...${NC}"
aws glue get-jobs --query "Jobs[?contains(Name, 'etl') || contains(Name, 'quality')].Name" --output table

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"

# Optional: Start a test run
read -p "Do you want to start a test run? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Starting test run...${NC}"
    
    aws glue start-job-run \
        --job-name ${GLUE_JOB_NAME} \
        --arguments '{
            "--S3_INPUT_PATH":"s3://your-bucket-name/raw/sample_sales_data.csv",
            "--S3_OUTPUT_PATH":"s3://your-bucket-name/processed/",
            "--REDSHIFT_TABLE":"sales_fact",
            "--JOB_RUN_ID":"test_'$(date +%Y%m%d_%H%M%S)'"
        }'
    
    echo -e "${GREEN}✓ Test run started. Check Glue console for status.${NC}"
fi
