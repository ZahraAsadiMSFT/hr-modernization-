# HR Document Generation System

An intelligent HR document generation system that converts natural language requests into SQL queries, processes data from Azure SQL Database, and generates formatted documents (Word/PDF) with cloud storage integration.

## Features

- **Natural Language Processing**: Convert plain English requests to SQL queries using Azure OpenAI GPT-4o
- **Multi-format Document Generation**: Generate Word payslips and PDF tax forms
- **Employee Search & Disambiguation**: Handle duplicate employee names with interactive selection
- **Token Usage Tracking**: Monitor AI model usage for cost optimization
- **Cloud Integration**: Azure SQL Database, Azure Blob Storage, and Azure OpenAI
- **Interactive CLI Interface**: User-friendly command-line interaction

## Architecture

```
User Input → AI Classification → SQL Query → Document Generation → Cloud Storage
```

- `app.py`: Main interactive system with Azure AD authentication
- `prompts.py`: AI classification engine with token tracking
- `payslip_fill.py`: Word document generation for payslips
- `pdf_fill.py`: PDF form filling for tax documents
- `inspect_pdfs.py`: PDF form field inspection utility

## Prerequisites

- Python 3.8+
- ODBC Driver 18 for SQL Server
- Azure services: SQL Database, Blob Storage, OpenAI

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TD-HR
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install ODBC Driver**
   Download and install "ODBC Driver 18 for SQL Server" from Microsoft.

4. **Configure environment**
   Copy `.env.example` to `.env` and update with your Azure credentials:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your actual Azure service details:
   ```env
   # SQL Database Connection  
   SQL_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};Server=tcp:YOUR-SERVER.database.windows.net,1433;Database=YOUR-DB;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;

   # Azure Blob Storage
   BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=YOUR-STORAGE;AccountKey=YOUR-KEY;EndpointSuffix=core.windows.net
   BLOB_CONTAINER_TEMPLATES=templates
   BLOB_CONTAINER_OUTPUT=output

   # Azure OpenAI
   AOAI_ENDPOINT=https://YOUR-AOAI.openai.azure.com/
   AOAI_API_KEY=YOUR-API-KEY
   AOAI_DEPLOYMENT=gpt-4o
   OPENAI_API_VERSION=2024-12-01-preview
   ```

5. **Set up the database**
   Run the provided SQL script to create sample data:
   ```bash
   # Connect to your Azure SQL Database and run:
   # database_setup.sql
   ```
   This creates tables, sample employees (including duplicate names for testing), and required stored procedures.

6. **Upload document templates**
   See `templates/README.md` for instructions on creating and uploading Word and PDF templates to your Azure Blob Storage.

## Quick Start

### Test with Sample Data

The easiest way to test the application:

1. **Run database setup**: Execute `database_setup.sql` in your Azure SQL Database
2. **Test the application**: 
   ```bash
   python app.py
   ```
3. **Try sample queries**:
   - "Get paystub for Alex Martin from January 2022"
   - "Generate T4 for Jordan Lee for 2023"

The sample data includes duplicate employee names (Alex Martin) to test the disambiguation feature.

## Usage

### Interactive Mode

Run the main application for an interactive experience:

```bash
python app.py
```

Example queries:
- "Get paystub for Alex Martin from January 2022"
- "Generate T4 for employee 12345 for year 2023"
- "Show pay summary for John Smith last quarter"

### PDF Form Inspection

Inspect available form fields in your PDF templates:

```bash
python inspect_pdfs.py
```

## Azure Setup Requirements

### Database Schema

Your Azure SQL Database should contain:

**Tables:**
- `Employees` - Employee master data (ID, name, contact details)
- `Payruns` - Payroll periods and calculations
- `Deductions` - Tax and benefit deductions
- `TaxSummary` - Annual tax summary data

**Required Stored Procedures:**
- `sp_GetPaystubForRange(@EmployeeNumber, @From, @To)` - Retrieve payslip data for date ranges
- `sp_GetT4Data(@EmployeeNumber, @Year)` - Retrieve T4 tax form data

### Blob Storage Containers

Create these containers in your Azure Storage Account:
- `templates` - Store document templates (payslip_template.docx, T4_template.pdf)
- `output` - Generated documents will be stored here

### Azure OpenAI

Deploy a GPT-4o model in your Azure OpenAI resource for natural language processing.

## Document Templates

Place your document templates in the Azure Blob Storage `templates` container:

- `payslip_template.docx`: Word template for payslips
- `T4_template.pdf`: Fillable PDF for T4 forms
- `T4A_template.pdf`: Fillable PDF for T4A forms

## Authentication

The system supports multiple Azure AD authentication methods:

1. Interactive authentication (browser-based)
2. Azure CLI credentials
3. Device code authentication

## Token Usage

The system tracks OpenAI token usage for cost monitoring. Token counts are displayed after each AI classification request.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Common Issues

**Database Connection Errors**
- Verify your connection string and Azure AD authentication
- Ensure your IP address is whitelisted in Azure SQL firewall

**PDF Form Errors**
- Use fillable PDF forms (not scanned documents)
- Run `inspect_pdfs.py` to verify field names match your templates

**Blob Storage Errors**
- Check storage account credentials and container permissions
- Verify container names match your configuration

**AI Classification Errors**
- Validate Azure OpenAI endpoint and API key
- Check deployment name and model availability

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with Azure OpenAI, Azure SQL Database, and Azure Blob Storage
- Uses tiktoken for token counting and cost monitoring
- Supports Word document generation and PDF form filling
