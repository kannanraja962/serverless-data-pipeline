#!/bin/bash

echo "========================================="
echo "Glue Jobs Status Monitor"
echo "========================================="
echo ""

# List all jobs
echo "Available Glue Jobs:"
aws glue get-jobs --query 'Jobs[*].Name' --output table

echo ""
echo "Recent Job Runs:"
echo ""

# Get recent runs for ETL job
GLUE_JOB_NAME="etl-sales-data"

aws glue get-job-runs \
    --job-name ${GLUE_JOB_NAME} \
    --max-results 10 \
    --query 'JobRuns[*].[Id,JobRunState,StartedOn,ExecutionTime,ErrorMessage]' \
    --output table

echo ""
echo "To get detailed info on a specific run:"
echo "aws glue get-job-run --job-name ${GLUE_JOB_NAME} --run-id <RUN_ID>"
