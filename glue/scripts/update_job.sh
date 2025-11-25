#!/bin/bash

S3_BUCKET="your-bucket-name"
S3_SCRIPT_PATH="s3://${S3_BUCKET}/scripts/"

echo "Uploading updated ETL script..."
aws s3 cp ../jobs/etl_job.py ${S3_SCRIPT_PATH}etl_job.py

echo "Uploading updated data quality script..."
aws s3 cp ../jobs/data_quality_check.py ${S3_SCRIPT_PATH}data_quality_check.py

echo "Scripts updated successfully!"
echo "Next Glue job run will use the new scripts."
