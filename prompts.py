import json
import os
import tiktoken
from openai import AzureOpenAI


def count_tokens(text, model="gpt-4o"):
    """
    Count tokens in text using tiktoken for the specified model
    
    Args:
        text: Text to count tokens for
        model: Model name (default: gpt-4o)
    
    Returns:
        int: Number of tokens
    """
    try:
        # Use gpt-4 encoding for gpt-4o (they use the same tokenizer)
        encoding = tiktoken.encoding_for_model("gpt-4")
        return len(encoding.encode(text))
    except Exception as e:
        print(f"Warning: Token counting failed ({e}), estimating...")
        # Rough estimate: ~4 characters per token
        return len(text) // 4


SYSTEM_PROMPT = """You classify HR document requests into one of these intents:
1) PAYSLIP_SELF {fromDate, toDate}
2) PAYSLIP_ON_BEHALF {employeeNumber, fromDate, toDate}
3) PAYSLIP_BY_NAME {employeeName, fromDate, toDate} - when employee name is provided instead of number
4) T4_SELF {year}
5) T4_ON_BEHALF {employeeNumber, year}
6) T4_BY_NAME {employeeName, year} - when employee name is provided instead of number
7) T4A_SELF {year}
8) T4A_ON_BEHALF {employeeNumber, year}
9) T4A_BY_NAME {employeeName, year} - when employee name is provided instead of number

Return JSON with: {"intent": "...", "parameters": {...}, "missing": [...]}

Examples:
- "Provide my paystub for March 2022" → {"intent": "PAYSLIP_SELF", "parameters": {"fromDate": "2022-03-01", "toDate": "2022-03-31"}, "missing": []}
- "Get T4 for employee 556677 for 2023" → {"intent": "T4_ON_BEHALF", "parameters": {"employeeNumber": "556677", "year": 2023}, "missing": []}
- "Get paystub for Alex Martin from January 2022" → {"intent": "PAYSLIP_BY_NAME", "parameters": {"employeeName": "Alex Martin", "fromDate": "2022-01-01", "toDate": "2022-01-31"}, "missing": []}
- "I need my T4 form" → {"intent": "T4_SELF", "parameters": {}, "missing": ["year"]}

If information is missing, list it in the "missing" array and ask for clarification.
Always extract dates in YYYY-MM-DD format. For month/year only requests, use first and last day of that period.
Use BY_NAME intents when a person's name (like "Alex", "John Smith", etc.) is mentioned instead of an employee number.
"""


def get_azure_openai_client():
    """Initialize Azure OpenAI client from environment variables"""
    try:
        return AzureOpenAI(
            api_key=os.environ["AOAI_API_KEY"],
            api_version=os.environ.get("OPENAI_API_VERSION", "2024-12-01-preview"),
            azure_endpoint=os.environ["AOAI_ENDPOINT"]
        )
    except TypeError as e:
        if "proxies" in str(e):
            # Handle version compatibility issue - use basic initialization
            return AzureOpenAI(
                api_key=os.environ["AOAI_API_KEY"],
                api_version=os.environ.get("OPENAI_API_VERSION", "2024-12-01-preview"),
                azure_endpoint=os.environ["AOAI_ENDPOINT"]
            )
        else:
            raise e


def classify_request(user_request, current_user_employee_number=None):
    """
    Classify a user request and extract parameters
    
    Args:
        user_request: The natural language request
        current_user_employee_number: The employee number of the current user (for _SELF requests)
    
    Returns:
        dict: Classification result with intent, parameters, missing fields, and token info
    """
    client = get_azure_openai_client()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_request}
    ]
    
    # Count input tokens
    input_text = SYSTEM_PROMPT + "\n" + user_request
    input_tokens = count_tokens(input_text)
    
    try:
        response = client.chat.completions.create(
            model=os.environ["AOAI_DEPLOYMENT"],
            messages=messages,
            temperature=0.1,
            max_tokens=500
        )
        
        raw_content = response.choices[0].message.content
        
        # Count output tokens
        output_tokens = count_tokens(raw_content)
        total_tokens = input_tokens + output_tokens
        
        # Create token info
        token_info = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        }
        
        # Display token information (optional - can be removed for production)
        print(f"Token usage - Input: {input_tokens:,}, Output: {output_tokens:,}, Total: {total_tokens:,}")
        
        if not raw_content or raw_content.strip() == "":
            return {
                "intent": "ERROR",
                "parameters": {},
                "missing": [],
                "error": "AI returned empty response",
                "token_info": token_info
            }
        
        # Handle markdown-wrapped JSON (remove ```json and ``` markers)
        json_content = raw_content.strip()
        if json_content.startswith("```json"):
            json_content = json_content[7:]  # Remove ```json
        if json_content.startswith("```"):
            json_content = json_content[3:]   # Remove ```
        if json_content.endswith("```"):
            json_content = json_content[:-3]  # Remove trailing ```
        json_content = json_content.strip()
        
        result = json.loads(json_content)
        
        # Add current user's employee number for _SELF requests
        if current_user_employee_number and result["intent"].endswith("_SELF"):
            result["parameters"]["employeeNumber"] = current_user_employee_number
        
        # Add token information to result
        result["token_info"] = token_info
        
        return result
        
    except json.JSONDecodeError as e:
        token_info = {"input_tokens": input_tokens, "output_tokens": 0, "total_tokens": input_tokens} if 'input_tokens' in locals() else {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        return {
            "intent": "ERROR",
            "parameters": {},
            "missing": [],
            "error": f"Failed to parse AI response: {e}. Raw response: '{raw_content if 'raw_content' in locals() else 'N/A'}'. Cleaned: '{json_content if 'json_content' in locals() else 'N/A'}'",
            "token_info": token_info
        }
    except Exception as e:
        token_info = {"input_tokens": input_tokens, "output_tokens": 0, "total_tokens": input_tokens} if 'input_tokens' in locals() else {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        return {
            "intent": "ERROR", 
            "parameters": {},
            "missing": [],
            "error": f"AI classification failed: {e}",
            "token_info": token_info
        }


def validate_parameters(intent, parameters):
    """
    Validate that all required parameters are present for the given intent
    
    Returns:
        list: Missing required parameters
    """
    required_params = {
        "PAYSLIP_SELF": ["employeeNumber", "fromDate", "toDate"],
        "PAYSLIP_ON_BEHALF": ["employeeNumber", "fromDate", "toDate"],
        "PAYSLIP_BY_NAME": ["employeeName", "fromDate", "toDate"],
        "T4_SELF": ["employeeNumber", "year"],
        "T4_ON_BEHALF": ["employeeNumber", "year"],
        "T4_BY_NAME": ["employeeName", "year"],
        "T4A_SELF": ["employeeNumber", "year"],
        "T4A_ON_BEHALF": ["employeeNumber", "year"],
        "T4A_BY_NAME": ["employeeName", "year"]
    }
    
    if intent not in required_params:
        return []
    
    missing = []
    for param in required_params[intent]:
        if param not in parameters or not parameters[param]:
            missing.append(param)
    
    return missing


def search_employees_by_name(cnxn, employee_name):
    """
    Search for employees by name and return matching records
    
    Args:
        cnxn: Database connection
        employee_name: Name to search for (can be partial)
    
    Returns:
        list: List of matching employee records with EmployeeNumber and FullName
    """
    with cnxn.cursor() as cur:
        # Search for employees with names containing the search term
        cur.execute("""
            SELECT DISTINCT EmployeeNumber, FullName
            FROM Employees 
            WHERE FullName LIKE ?
            ORDER BY FullName
        """, (f"%{employee_name}%",))
        
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def confirm_employee_selection(matches, requested_name):
    """
    Handle employee selection when multiple matches are found
    
    Args:
        matches: List of employee records
        requested_name: The name that was originally requested
    
    Returns:
        str: Selected employee number or None if cancelled
    """
    if not matches:
        print(f"No employees found matching '{requested_name}'")
        return None
    
    if len(matches) == 1:
        employee = matches[0]
        print(f"Found employee: {employee['FullName']} (ID: {employee['EmployeeNumber']})")
        confirm = input("Is this correct? (y/n): ").strip().lower()
        if confirm == 'y':
            return employee['EmployeeNumber']
        else:
            return None
    
    # Multiple matches found
    print(f"\nMultiple employees found matching '{requested_name}':")
    for i, employee in enumerate(matches, 1):
        print(f"  {i}. {employee['FullName']} (ID: {employee['EmployeeNumber']})")
    
    while True:
        try:
            choice = input(f"Select employee (1-{len(matches)}) or 'c' to cancel: ").strip()
            if choice.lower() == 'c':
                return None
            
            index = int(choice) - 1
            if 0 <= index < len(matches):
                selected = matches[index]
                print(f"Selected: {selected['FullName']} (ID: {selected['EmployeeNumber']})")
                return selected['EmployeeNumber']
            else:
                print(f"Please enter a number between 1 and {len(matches)}")
        except ValueError:
            print("Please enter a valid number or 'c' to cancel")


# Example usage (for testing)

