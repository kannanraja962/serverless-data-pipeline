#!/bin/bash

FUNCTION_NAME="serverless-pipeline-s3-trigger"
ROLE_ARN="arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role"

# Package Lambda function
zip -r function.zip handler.py

# Create/Update Lambda function
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://function.zip

echo "Lambda function deployed successfully!"
