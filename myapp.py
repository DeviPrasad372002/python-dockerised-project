from flask import Flask, request, flash, redirect, url_for, render_template
import boto3
import os
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from dotenv import load_dotenv
load_dotenv()

# Load environment variables from .env file
#load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

# AWS Credentials from Environment Variables
aws_creds = {
    "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
    "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "AWS_DEFAULT_REGION": os.getenv("AWS_DEFAULT_REGION"),
}

# Validate Required Credentials
required_keys = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"]
for key in required_keys:
    if not aws_creds.get(key):
        raise ValueError(f"Missing required AWS credential: {key}")

# Initialize S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=aws_creds["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=aws_creds["AWS_SECRET_ACCESS_KEY"],
    region_name=aws_creds["AWS_DEFAULT_REGION"]
)

# Function: List S3 Buckets
def list_s3_buckets():
    try:
        response = s3.list_buckets()
        return [bucket["Name"] for bucket in response.get("Buckets", [])]
    except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
        flash(f"Error listing buckets: {str(e)}", "danger")
        return []

# Function: Create S3 Bucket
def create_s3_bucket(bucket_name):
    try:
        region = aws_creds["AWS_DEFAULT_REGION"]
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region}
            )
        flash(f"Bucket {bucket_name} created successfully!", "success")
    except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
        flash(f"Create failed: {str(e)}", "danger")

# Function: Delete S3 Bucket
def delete_s3_bucket(bucket_name):
    try:
        s3.delete_bucket(Bucket=bucket_name)
        flash(f"Bucket {bucket_name} deleted!", "danger")
    except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
        flash(f"Delete failed: {str(e)}", "danger")

# Function: List Files in a Selected S3 Bucket
def list_s3_files(bucket_name):
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        return response.get("Contents", []) if "Contents" in response else []
    except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
        flash(f"Error listing files in {bucket_name}: {str(e)}", "danger")
        return []

# Route: Home (List Buckets & Default Bucket Files)
@app.route("/")
def index():
    buckets = list_s3_buckets()
    selected_bucket = request.args.get("bucket", buckets[0] if buckets else None)
    files = list_s3_files(selected_bucket) if selected_bucket else []
    return render_template("index.html", buckets=buckets, selected_bucket=selected_bucket, files=files)

# Route: Create Bucket
@app.route("/create_bucket", methods=["POST"])
def create_bucket():
    bucket_name = request.form.get("bucket_name")
    if bucket_name:
        create_s3_bucket(bucket_name)
    return redirect(url_for("index"))

# Route: View Files from a Selected Bucket
@app.route("/view_bucket/<bucket_name>")
def view_bucket(bucket_name):
    buckets = list_s3_buckets()
    files = list_s3_files(bucket_name)
    return render_template("index.html", buckets=buckets, selected_bucket=bucket_name, files=files)

# Route: Upload File
@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files.get("file")
        bucket_name = request.form.get("bucket")
        if file and bucket_name:
            try:
                s3.upload_fileobj(file, bucket_name, file.filename)
                flash("File uploaded successfully!", "success")
            except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
                flash(f"Upload failed: {str(e)}", "danger")
            return redirect(url_for("index"))
    return render_template("upload.html", buckets=list_s3_buckets())

# Route: Delete File
@app.route("/delete/<bucket_name>/<filename>")
def delete_file(bucket_name, filename):
    try:
        s3.delete_object(Bucket=bucket_name, Key=filename)
        flash(f"{filename} deleted from {bucket_name}!", "danger")
    except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
        flash(f"Delete failed: {str(e)}", "danger")
    return redirect(url_for("index", bucket=bucket_name))

# Route: Copy File
@app.route("/copy/<bucket_name>/<filename>")
def copy_file(bucket_name, filename):
    try:
        copy_source = {"Bucket": bucket_name, "Key": filename}
        new_key = f"copy_of_{filename}"
        s3.copy_object(Bucket=bucket_name, CopySource=copy_source, Key=new_key)
        flash(f"Copied {filename} to {new_key} in {bucket_name}!", "info")
    except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
        flash(f"Copy failed: {str(e)}", "danger")
    return redirect(url_for("index", bucket=bucket_name))

# Route: Move File (Copy & Delete)
@app.route("/move/<bucket_name>/<filename>/<new_folder>")
def move_file(bucket_name, filename, new_folder):
    try:
        copy_source = {"Bucket": bucket_name, "Key": filename}
        new_key = f"{new_folder}/{filename}"
        s3.copy_object(Bucket=bucket_name, CopySource=copy_source, Key=new_key)
        s3.delete_object(Bucket=bucket_name, Key=filename)
        flash(f"Moved {filename} to {new_folder} in {bucket_name}!", "warning")
    except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
        flash(f"Move failed: {str(e)}", "danger")
    return redirect(url_for("index", bucket=bucket_name))

# Route: Delete Bucket
@app.route("/delete_bucket", methods=["POST"])
def delete_bucket():
    bucket_name = request.form.get("bucket_name")
    if bucket_name:
        delete_s3_bucket(bucket_name)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=5002)
