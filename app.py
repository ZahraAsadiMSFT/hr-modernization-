import os
import pyodbc
import json
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from payslip_fill import fetch_paystub_rows, render_payslip_docx, upload_bytes_to_blob
from pdf_fill import (
    download_blob_bytes, 
    list_pdf_fields, 
    fill_pdf_fields, 
    upload_blob_bytes,
    fetch_tax_form_data,
    create_t4_field_map,
    create_t4a_field_map
)
from prompts import classify_request, validate_parameters, search_employees_by_name, confirm_employee_selection

# Load environment variables
load_dotenv()

# Session token tracking
session_token_tracker = {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_tokens": 0,
    "request_count": 0
}

def get_db_connection():
    """Create database connection using Azure Identity"""
    try:
        # Try Azure AD Interactive authentication (should work with Microsoft accounts)
        # Extract server and database from environment connection string
        base_conn = os.environ["SQL_CONNECTION_STRING"].strip('"')
        
        # Extract server and database properly
        server_part = [part for part in base_conn.split(";") if part.startswith("Server=")][0]
        server = server_part.split("=", 1)[1]
        
        database_part = [part for part in base_conn.split(";") if part.startswith("Database=")][0]
        database = database_part.split("=", 1)[1]
        
        conn_str = (
            "Driver={ODBC Driver 18 for SQL Server};"
            f"Server={server};"
            f"Database={database};"
            "Authentication=ActiveDirectoryInteractive;"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )
        print("Attempting Azure AD Interactive authentication (may open browser)...")
        return pyodbc.connect(conn_str)
        
    except Exception as e:
        print(f"Azure AD Interactive failed ({e})")
        
        try:
            # Try Azure CLI credential with proper token handling
            from azure.identity import AzureCliCredential
            credential = AzureCliCredential()
            token = credential.get_token("https://database.windows.net/")
            
            # Build connection string without Authentication parameter
            base_conn = os.environ["SQL_CONNECTION_STRING"].strip('"')
            
            # Extract server and database properly
            server_part = [part for part in base_conn.split(";") if part.startswith("Server=")][0]
            server = server_part.split("=", 1)[1]
            
            database_part = [part for part in base_conn.split(";") if part.startswith("Database=")][0]
            database = database_part.split("=", 1)[1]
            
            conn_str = (
                "Driver={ODBC Driver 18 for SQL Server};"
                f"Server={server};"
                f"Database={database};"
                "Encrypt=yes;"
                "TrustServerCertificate=no;"
                "Connection Timeout=30;"
            )
            
            # Use the token directly
            conn = pyodbc.connect(conn_str, attrs_before={
                1256: token.token.encode('utf-16-le')  # SQL_COPT_SS_ACCESS_TOKEN
            })
            print("Azure CLI credential authentication successful")
            return conn
            
        except Exception as e2:
            print(f"Azure CLI authentication failed ({e2})")
            
            try:
                # Try Azure AD Device Code authentication
                base_conn = os.environ["SQL_CONNECTION_STRING"].strip('"')
                
                # Extract server and database properly
                server_part = [part for part in base_conn.split(";") if part.startswith("Server=")][0]
                server = server_part.split("=", 1)[1]
                
                database_part = [part for part in base_conn.split(";") if part.startswith("Database=")][0]
                database = database_part.split("=", 1)[1]
                
                conn_str = (
                    "Driver={ODBC Driver 18 for SQL Server};"
                    f"Server={server};"
                    f"Database={database};"
                    "Authentication=ActiveDirectoryDeviceCodeFlow;"
                    "Encrypt=yes;"
                    "TrustServerCertificate=no;"
                    "Connection Timeout=30;"
                )
                print("Attempting Azure AD Device Code authentication...")
                return pyodbc.connect(conn_str)
                
            except Exception as e3:
                # Last fallback to SQL authentication 
                print(f"All Azure AD methods failed ({e3}), trying SQL authentication...")
                return pyodbc.connect(os.environ["SQL_CONNECTION_STRING"])

def interactive_hr_system():
    """Interactive HR document generation - exactly what you asked for"""
    print("HR DOCUMENT GENERATION SYSTEM")
    print("=" * 50)
    print("Enter your query and I'll:")
    print("1. Convert your natural language to SQL query")
    print("2. Query the Azure SQL database")
    print("3. Map data to payslip_template.docx")
    print("4. Store result in output container")
    print()
    
    while True:
        # Step 1: Get user query
        print("What is your query? (or 'quit' to exit)")
        user_query = input("   > ").strip()
        
        if user_query.lower() in ['quit', 'exit', 'q']:
            # Display session summary before exiting
            print("\nSESSION TOKEN SUMMARY")
            print("=" * 30)
            print(f"Total Requests: {session_token_tracker['request_count']}")
            print(f"Total Input Tokens: {session_token_tracker['total_input_tokens']:,}")
            print(f"Total Output Tokens: {session_token_tracker['total_output_tokens']:,}")
            print(f"Total Tokens: {session_token_tracker['total_tokens']:,}")
            break
            
        if not user_query:
            continue
            
        print(f"\nProcessing: '{user_query}'")
        print("-" * 50)
        
        try:
            # Step 2: Convert to SQL query parameters
            print("Step 1: Converting natural language to SQL parameters...")
            classification = classify_request(user_query, current_user_employee_number="102938")
            
            # Track tokens
            if 'token_info' in classification:
                token_info = classification['token_info']
                session_token_tracker['total_input_tokens'] += token_info.get('input_tokens', 0)
                session_token_tracker['total_output_tokens'] += token_info.get('output_tokens', 0)
                session_token_tracker['total_tokens'] += token_info.get('total_tokens', 0)
                session_token_tracker['request_count'] += 1
            
            if classification['intent'] == 'ERROR':
                print(f"Could not understand query: {classification.get('error')}")
                continue
                
            print(f"   Intent: {classification['intent']}")
            print(f"   Parameters: {classification['parameters']}")
            
            # Step 3: Query the Azure SQL database
            print("\nStep 2: Querying Azure SQL database...")
            
            if 'PAYSLIP' in classification['intent']:
                params = classification['parameters']
                
                # Handle name-based searches
                if 'BY_NAME' in classification['intent']:
                    employee_name = params['employeeName']
                    print(f"   Searching for employee: '{employee_name}'")
                    
                    # Get database connection for employee search
                    cnxn = get_db_connection()
                    matches = search_employees_by_name(cnxn, employee_name)
                    
                    if not matches:
                        print(f"No employees found matching '{employee_name}'")
                        cnxn.close()
                        continue
                    
                    # Get employee confirmation
                    employee_number = confirm_employee_selection(matches, employee_name)
                    if not employee_number:
                        print("Operation cancelled")
                        cnxn.close()
                        continue
                    
                    # Update parameters with confirmed employee number
                    params['employeeNumber'] = employee_number
                    cnxn.close()
                
                employee_number = params['employeeNumber']
                from_date = params['fromDate']
                to_date = params['toDate']
                
                print(f"   SQL: EXEC sp_GetPaystubForRange @EmployeeNumber='{employee_number}', @From='{from_date}', @To='{to_date}'")
                
                cnxn = get_db_connection()
                rows = fetch_paystub_rows(cnxn, employee_number, from_date, to_date)
                cnxn.close()
                
                if not rows:
                    print(f"No data found for employee {employee_number} in date range")
                    continue
                    
                print(f"Found {len(rows)} pay periods for {rows[0]['FullName']}")
                
                # Step 4: Map to payslip_template.docx
                print("\nStep 3: Mapping data to payslip_template.docx...")
                doc_buffer = render_payslip_docx(rows)
                doc_bytes = doc_buffer.getvalue()
                print(f"   Document generated: {len(doc_bytes):,} bytes")
                
                # Step 5: Store in output container
                print("\nStep 4: Storing in output container...")
                employee_name = rows[0]['FullName'].replace(' ', '_')
                filename = f"paystub_{employee_name}_{from_date.replace('-', '')}_to_{to_date.replace('-', '')}.docx"
                
                upload_bytes_to_blob("output", filename, doc_bytes)
                
                # Show result
                blob_cs = os.environ["BLOB_CONNECTION_STRING"].strip('"')
                account_name = blob_cs.split("AccountName=")[1].split(";")[0]
                download_url = f"https://{account_name}.blob.core.windows.net/output/{filename}"
                
                print(f"Success! Document stored as: {filename}")
                print(f"Download: {download_url}")
                
            else:
                print(f"Only paystub requests supported in this demo")
                
        except Exception as e:
            print(f"Error: {e}")
            
        print(f"\n" + "=" * 50)

if __name__ == "__main__":
    interactive_hr_system()
