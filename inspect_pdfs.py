"""
Simple test script to inspect PDF form fields
Run this first to understand what fields are available in your T4/T4A templates
"""
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from pypdf import PdfReader
import io

load_dotenv()

def list_pdf_fields(pdf_bytes):
    """List all fillable fields in a PDF form"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    fields = reader.get_fields() or {}
    return list(fields.keys())

def inspect_pdf_templates():
    """Inspect the PDF templates to see available form fields"""
    
    # Try Azure Identity first, then fall back to connection string
    try:
        # Use Azure Identity (recommended for production)
        credential = DefaultAzureCredential()
        # Extract storage account name from connection string
        blob_cs = os.environ["BLOB_CONNECTION_STRING"]
        account_name = blob_cs.split("AccountName=")[1].split(";")[0]
        storage_url = f"https://{account_name}.blob.core.windows.net"
        blob_client = BlobServiceClient(account_url=storage_url, credential=credential)
        print("Using Azure Identity authentication")
    except Exception as e:
        print(f"Azure Identity failed ({e}), trying connection string...")
        try:
            blob_client = BlobServiceClient.from_connection_string(os.environ["BLOB_CONNECTION_STRING"])
            print("Using connection string authentication")
        except Exception as e2:
            print(f"Error: Both authentication methods failed: {e2}")
            return
    
    templates_container = os.environ.get("BLOB_CONTAINER_TEMPLATES", "templates")
    pdf_files = ["t4-fill-24e.pdf", "t4a-fill-24e.pdf"]
    
    for pdf_file in pdf_files:
        print(f"\n=== Inspecting {pdf_file} ===")
        try:
            # Download the PDF
            blob_data = blob_client.get_blob_client(container=templates_container, blob=pdf_file).download_blob()
            pdf_bytes = blob_data.readall()
            print(f"Downloaded {pdf_file} ({len(pdf_bytes)} bytes)")
            
            # List form fields
            fields = list_pdf_fields(pdf_bytes)
            
            if fields:
                print(f"📋 Found {len(fields)} form fields:")
                for i, field in enumerate(fields, 1):
                    print(f"  {i:2d}. {field}")
            else:
                print("Warning: No form fields found - PDF might not be a fillable form")
                
        except Exception as e:
            print(f"Error inspecting {pdf_file}: {e}")

if __name__ == "__main__":
    print("PDF Template Field Inspector")
    print("=" * 40)
    inspect_pdf_templates()
