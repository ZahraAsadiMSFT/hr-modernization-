# Sample Document Templates Setup

This directory contains sample document templates for testing the HR Document Generation System.

## Required Templates

To run the application, you need these document templates in your Azure Blob Storage `templates` container:

### 1. `payslip_template.docx` - Word Payslip Template
A Microsoft Word document with the following bookmark placeholders:
- `{{FullName}}` - Employee full name
- `{{EmployeeNumber}}` - Employee ID number  
- `{{PeriodStart}}` - Pay period start date
- `PeriodEnd}}` - Pay period end date
- `{{GrossAmount}}` - Gross pay amount
- `{{NetAmount}}` - Net pay amount
- `{{CPP}}` - Canada Pension Plan deduction
- `{{EI}}` - Employment Insurance deduction

### 2. `T4_template.pdf` - T4 Tax Form Template  
A fillable PDF form with Canadian Revenue Agency T4 fields. Common field names include:
- Employee information fields
- Box 14 (Employment income)
- Box 22 (Income tax deducted)

### 3. `T4A_template.pdf` - T4A Tax Form Template
A fillable PDF form for T4A tax documents.

## Creating Your Own Templates

### Word Template (.docx)
1. Create a Word document with your desired layout
2. Insert bookmarks using Insert → Links → Bookmark
3. Use the placeholder names listed above (with double curly braces)
4. Save as `payslip_template.docx`

### PDF Templates (.pdf)
1. Download fillable T4/T4A forms from Canada Revenue Agency website
2. Or create your own fillable PDF using Adobe Acrobat or similar tools
3. Use `inspect_pdfs.py` to discover the exact field names in your PDFs
4. Update the field mapping in `pdf_fill.py` if needed

## Upload to Azure Blob Storage

Upload these templates to your Azure Blob Storage `templates` container:

```bash
# Using Azure CLI
az storage blob upload --account-name YOUR-STORAGE --container-name templates --name payslip_template.docx --file payslip_template.docx
az storage blob upload --account-name YOUR-STORAGE --container-name templates --name T4_template.pdf --file T4_template.pdf
az storage blob upload --account-name YOUR-STORAGE --container-name templates --name T4A_template.pdf --file T4A_template.pdf
```

## Testing Template Discovery

Use the included utility to inspect your PDF templates:

```bash
python inspect_pdfs.py
```

This will show you all available form fields in your PDF templates, which you can then map in the application code.
