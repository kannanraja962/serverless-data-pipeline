import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from datetime import datetime

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'S3_INPUT_PATH',
    'S3_OUTPUT_PATH',
    'REDSHIFT_TABLE'
])

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print(f"Starting ETL job for: {args['S3_INPUT_PATH']}")

# Read raw data from S3
df = spark.read.option("header", "true").csv(args['S3_INPUT_PATH'])

print(f"Raw data loaded: {df.count()} records")

# Data Transformations
df_cleaned = df \
    .filter(col("order_id").isNotNull()) \
    .filter(col("sales_amount").cast("double") > 0) \
    .dropDuplicates(["order_id"]) \
    .withColumn("order_date", to_date(col("order_date"), "yyyy-MM-dd")) \
    .withColumn("sales_amount", col("sales_amount").cast("double")) \
    .withColumn("quantity", col("quantity").cast("int")) \
    .withColumn("processed_timestamp", lit(datetime.now()))

# Add derived columns
df_transformed = df_cleaned \
    .withColumn("year", year(col("order_date"))) \
    .withColumn("month", month(col("order_date"))) \
    .withColumn("quarter", quarter(col("order_date"))) \
    .withColumn("revenue", col("sales_amount") * col("quantity"))

print(f"Data cleaned and transformed: {df_transformed.count()} records")

# Write to S3 in Parquet format (optimized for Redshift)
output_path = f"{args['S3_OUTPUT_PATH']}/processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
df_transformed.write \
    .mode("overwrite") \
    .parquet(output_path)

print(f"Processed data written to: {output_path}")

# Load to Redshift using COPY command
redshift_options = {
    "url": "jdbc:redshift://your-cluster.region.redshift.amazonaws.com:5439/analytics_db",
    "dbtable": args['REDSHIFT_TABLE'],
    "user": "admin",
    "password": "YourPassword123!",
    "aws_iam_role": "arn:aws:iam::123456789012:role/RedshiftCopyRole"
}

df_transformed.write \
    .format("io.github.spark_redshift_community.spark.redshift") \
    .options(**redshift_options) \
    .option("tempdir", f"{args['S3_OUTPUT_PATH']}/temp/") \
    .mode("append") \
    .save()

print(f"Data loaded to Redshift table: {args['REDSHIFT_TABLE']}")

job.commit()
