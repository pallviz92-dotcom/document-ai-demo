# Import Document AI API client
from dotenv import load_dotenv
import os
from sap_business_document_processing import DoxApiClient
import json
from utils import display_capabilities
from sap_business_document_processing.document_information_extraction_client.constants import CONTENT_TYPE_PDF

# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables
url = os.getenv('URL')
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
uaa_url = os.getenv('UAADOMAIN')

# Instantiate object used to communicate with Document AI REST API
api_client = DoxApiClient(url, client_id, client_secret, uaa_url)

# Get the available document types and corresponding extraction fields
capabilities = api_client.get_capabilities()
display_capabilities(capabilities)

# Optional: Check which clients exist for this tenant
# api_client.get_clients()
# Optional: Create a new client with the id 'c_00' and name 'Client 00'
# api_client.create_client(client_id='c_00', client_name='Client 00')

# Supported content types: CONTENT_TYPE_PDF, CONTENT_TYPE_PNG, CONTENT_TYPE_JPEG,
# CONTENT_TYPE_TIFF, or CONTENT_TYPE_UNKNOWN (auto-detect from file extension)

# Specify the fields that should be extracted
header_fields = [
    "documentNumber",
    "taxId",
    "purchaseOrderNumber",
    "shippingAmount",
    "netAmount",
    "senderAddress",
    "senderName",
    "grossAmount",
    "currencyCode",
    "receiverContact",
    "documentDate",
    "taxAmount",
    "taxRate",
    "receiverName",
    "receiverAddress",
]
line_item_fields = [
    "description",
    "netAmount",
    "quantity",
    "unitPrice",
]

# Extract information from invoice document
document_result = api_client.extract_information_from_document(
    document_path='bills_data/jan_bill_download.pdf',
    client_id='default',
    document_type='invoice',
    mime_type=CONTENT_TYPE_PDF,
    header_fields=header_fields,
    line_item_fields=line_item_fields,
)

# Save the extracted data to result.json
json_object = json.dumps(document_result, indent=2)
with open("result.json", "w") as outfile:
    outfile.write(json_object)

print("Extraction complete. Results written to result.json")
