import sys
from flask import Flask, render_template, request
from azure.storage.blob import BlobServiceClient
from azure.storage.fileshare import ShareServiceClient
import json
import os
# Set the path where Azure File Share is mounted
CONFIG_FILE_PATH = "/azurefiles/azurefiles/config.py" # Adjust if running locally


# Dynamically load config.py from Azure File Share
if os.path.exists(CONFIG_FILE_PATH):
    sys.path.append(os.path.dirname(CONFIG_FILE_PATH))
    import config
else:
    raise FileNotFoundError("Config file not found in Azure File Share!")

app = Flask(__name__)

# Initialize Azure Blob Client
blob_service_client = BlobServiceClient.from_connection_string(config.AZURE_CONNECTION_STRING)
blob_container_client = blob_service_client.get_container_client(config.AZURE_BLOB_CONTAINER_NAME)

# Initialize Azure File Share Client
file_share_client = ShareServiceClient.from_connection_string(config.AZURE_CONNECTION_STRING)
file_client = file_share_client.get_share_client(config.AZURE_FILE_SHARE_NAME)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    name = request.form.get("firstname")
    surname = request.form.get("lastname")
    file = request.files["file"]

    if not name or not surname or not file:
        return "All fields are required!", 400

    # Upload file to Azure Blob Storage
    blob_client = blob_container_client.get_blob_client(file.filename)
    file_contents = file.read()  # Read file before upload
    blob_client.upload_blob(file_contents, overwrite=True)

    # Generate Blob URL
    blob_url = f"https://{config.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{config.AZURE_BLOB_CONTAINER_NAME}/{file.filename}"

    # Prepare Data to Save in Azure File Share
    text_data = f"Name: {name}\nSurname: {surname}\nUploaded File URL: {blob_url}"
    file_share_path = f"user_data_{name}_{surname}.txt"

    # Upload File Info to Azure File Share
    try:
        directory_client = file_client.get_directory_client("")
        file_client_instance = directory_client.get_file_client(file_share_path)
        file_client_instance.create_file(len(text_data))
        file_client_instance.upload_file(text_data)
    except Exception as e:
        return f"Error saving file metadata: {str(e)}", 500

    return "Data and file uploaded successfully!"


if __name__ == "__main__":
    app.run(debug=True)
