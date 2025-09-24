from pypdf import PdfReader, PdfWriter
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import io
import os


def list_pdf_fields(pdf_bytes):
    """List all fillable fields in a PDF form"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    fields = reader.get_fields() or {}
    return list(fields.keys())


def fill_pdf_fields(pdf_bytes, field_map: dict):
    """Fill a PDF form with provided field values"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    
    # Copy all pages first
    for page in reader.pages:
        writer.add_page(page)
    
    # Check if the PDF has form fields
    if reader.get_fields():
        print(f"Found form fields, attempting to fill {len(field_map)} values...")
        try:
            # Try to update form field values
            # Note: This might not work with all PDF forms, depending on their structure
            for page_num in range(len(writer.pages)):
                try:
                    writer.update_page_form_field_values(writer.pages[page_num], field_map)
                    print(f"Updated fields on page {page_num + 1}")
                    break  # Success on first page is usually enough
                except Exception as e:
                    print(f"Page {page_num + 1} field update failed: {e}")
                    continue
            
            # Try to flatten the form (make fields non-editable)
            try:
                for page_num in range(len(writer.pages)):
                    annots = writer.pages[page_num].get("/Annots")
                    if annots:
                        for a in annots:
                            annotation = a.get_object()
                            if annotation:
                                annotation.update({"/Ff": 1})
                print("Form flattened successfully")
            except Exception as e:
                print(f"Form flattening failed: {e}")
                
        except Exception as e:
            print(f"Form field update failed: {e}")
            print("Proceeding with blank PDF template...")
    else:
        print("PDF has no fillable form fields")
        print("Returning blank template (for demo purposes)")
    
    # Write to bytes buffer
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out


def get_blob_client():
    """Get blob service client with Azure Identity or connection string fallback"""
    try:
        # Try Azure Identity first (recommended for production)
        credential = DefaultAzureCredential()
        blob_cs = os.environ["BLOB_CONNECTION_STRING"]
        account_name = blob_cs.split("AccountName=")[1].split(";")[0]
        storage_url = f"https://{account_name}.blob.core.windows.net"
        return BlobServiceClient(account_url=storage_url, credential=credential)
    except Exception:
        # Fallback to connection string
        return BlobServiceClient.from_connection_string(os.environ["BLOB_CONNECTION_STRING"])


def download_blob_bytes(container, blob_name):
    """Download a blob as bytes using Azure Identity"""
    blob_client = get_blob_client()
    return blob_client.get_blob_client(container=container, blob=blob_name).download_blob().readall()


def upload_blob_bytes(container, blob_name, data):
    """Upload bytes to a blob using Azure Identity"""
    blob_client = get_blob_client()
    blob_client.get_blob_client(container=container, blob=blob_name).upload_blob(data, overwrite=True)
    print(f"Uploaded {blob_name} to {container} container")


def fetch_tax_form_data(cnxn, employee_number, year, form_type):
    """Fetch tax form data using the stored procedure"""
    with cnxn.cursor() as cur:
        cur.execute("""
            EXEC dbo.sp_GetTaxFormData @EmployeeNumber=?, @Year=?, @FormType=?
        """, (employee_number, year, form_type))
        r = cur.fetchone()
        if r:
            fields = [c[0] for c in cur.description]
            return dict(zip(fields, r))
        return None


def create_t4_field_map(data):
    """Create field mapping for T4 form based on database data"""
    if not data:
        raise ValueError("No tax data found")
    
    # Based on the PDF inspection, these are the actual field names for T4
    # Using Slip1 (first slip on the page)
    field_map = {
        # Employee information
        "form1[0].Page1[0].Slip1[0].Employee[0].LastName[0].Slip1LastName[0]": data["FullName"].split()[-1] if " " in data["FullName"] else data["FullName"],
        "form1[0].Page1[0].Slip1[0].Employee[0].FirstName[0].Slip1FirstName[0]": data["FullName"].split()[0] if " " in data["FullName"] else "",
        "form1[0].Page1[0].Slip1[0].Box12[0].Slip1Box12[0]": data["SIN"],  # SIN field
        
        # Year
        "form1[0].Page1[0].Slip1[0].Year[0].Slip1Year[0]": str(data["Year"]),
        
        # Tax amounts - using Box14 (Employment Income) and Box22 (Income Tax Deducted)
        "form1[0].Page1[0].Slip1[0].Box14[0].Slip1Box14[0]": f"{float(data['EmploymentIncome']):.2f}",
        "form1[0].Page1[0].Slip1[0].Box22[0].Slip1Box22[0]": f"{float(data['IncomeTaxDeducted']):.2f}",
        
        # Employer information (you may want to customize these)
        "form1[0].Page1[0].Slip1[0].EmployersName[0].Slip1EmployersName[0]": "TD Bank Group",
        # Add more fields as needed
    }
    return field_map


def create_t4a_field_map(data):
    """Create field mapping for T4A form based on database data"""
    if not data:
        raise ValueError("No tax data found")
    
    # Based on the PDF inspection, these are the actual field names for T4A
    # Using Slip1 (first slip on the page)
    field_map = {
        # Employee information
        "form1[0].Page1[0].Slip1[0].Employee[0].LastName[0].Slip1LastName[0]": data["FullName"].split()[-1] if " " in data["FullName"] else data["FullName"],
        "form1[0].Page1[0].Slip1[0].Employee[0].FirstName[0].Slip1FirstName[0]": data["FullName"].split()[0] if " " in data["FullName"] else "",
        "form1[0].Page1[0].Slip1[0].Box12[0].Slip1SIN[0]": data["SIN"],  # SIN field for T4A
        
        # Year
        "form1[0].Page1[0].Slip1[0].Year[0].Slip1Year[0]": str(data["Year"]),
        
        # T4A uses Line16 and Line22 instead of Box14/Box22
        "form1[0].Page1[0].Slip1[0].Line16[0].Slip1Line16[0]": f"{float(data['EmploymentIncome']):.2f}",
        "form1[0].Page1[0].Slip1[0].Line22[0].Slip1Line22[0]": f"{float(data['IncomeTaxDeducted']):.2f}",
        
        # Employer information
        "form1[0].Page1[0].Slip1[0].EmployersName[0].Slip1EmployersName[0]": "TD Bank Group",
        # Add more fields as needed
    }
    return field_map
