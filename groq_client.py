import os
import re
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from dotenv import load_dotenv

load_dotenv()

class IncidentSchema(BaseModel):
    Severity: str = Field(
        description="""Severity based on impact:
        - High: Critical outage, production down, >500 users affected
        - Med: Significant issue, partial outage, 100-500 users affected  
        - Low: Minor issue, performance degradation, <100 users affected
        Output MUST be exactly: 'High', 'Med', or 'Low'""",
        enum=["High", "Med", "Low"]
    )
    Component: str = Field(description="The affected system component")
    Timestamp: str = Field(
        description="""Extract the time mentioned in the incident report.
        Examples: '6:30 PM', '2:00 AM', 'around midnight', 'at 3 PM'
        If no time is mentioned, use 'Unknown'""",
        default="Unknown"
    )
    Suspected_Cause: str = Field(description="Short phrase for suspected cause")
    Impact_Count: int = Field(description="Number of users affected")

def extract_timestamp_from_text(text: str) -> str:
    """Extract timestamp from text using regex patterns."""
    # Common time patterns
    time_patterns = [
        r'(\d{1,2}:\d{2}\s*(?:[AP]M|[ap]m))',  # 6:30 PM
        r'(\d{1,2}\s*(?:[AP]M|[ap]m))',        # 6 PM
        r'at\s+(\d{1,2}(?::\d{2})?)',          # at 6:30 or at 6
        r'(\d{1,2}) o\'?clock',                # 6 o'clock
        r'(noon|midnight)',                    # noon/midnight
        r'(\d{1,2})\s*(?:am|pm)',              # 6pm (no space)
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            time_str = match.group(1)
            # Clean up
            time_str = time_str.strip()
            # Convert to standard format
            if time_str.lower() == 'noon':
                return '12:00 PM'
            elif time_str.lower() == 'midnight':
                return '12:00 AM'
            # Ensure AM/PM is uppercase
            if 'am' in time_str.lower() or 'pm' in time_str.lower():
                time_str = time_str.upper()
            return time_str
    
    # Check for relative times
    relative_patterns = [
        r'(morning|afternoon|evening|night)',
        r'(today|yesterday|tomorrow)',
    ]
    
    for pattern in relative_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).title()
    
    return "Unknown"

def call_groq_api_structured(text: str) -> dict:
    """Main function using LangChain structured output."""
    llm = ChatGroq(
        temperature=0.1,
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
    )
    
    parser = PydanticOutputParser(pydantic_object=IncidentSchema)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an incident analyst. Extract data accurately.
        
        Severity Guidelines:
        1. HIGH: Production systems down, critical failures, >500 users impacted
        2. MED: Partial outages, degraded performance, 100-500 users impacted  
        3. LOW: Minor issues, warnings, <100 users impacted
        
        Timestamp: Extract ANY time mentioned. Look for:
        - Exact times: '6:30 PM', '2:00 AM'
        - Approximate: 'around 3 PM', 'about midnight'
        - Relative: 'this morning', 'yesterday afternoon'
        - Only use 'Unknown' if NO time reference at all
        
        {format_instructions}"""),
        ("user", "Analyze this incident report: {text}")
    ])
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "text": text,
            "format_instructions": parser.get_format_instructions()
        })
        data = result.dict()
        
        # ===== POST-PROCESSING FIXES =====
        
        # 1. Fix Severity based on Impact_Count
        impact = data.get("Impact_Count", 0)
        current_severity = data.get("Severity", "Med")
        
        if impact >= 500 and current_severity != "High":
            data["Severity"] = "High"
        elif impact >= 100 and current_severity == "Low":
            data["Severity"] = "Med"
        elif impact < 100 and current_severity == "High":
            data["Severity"] = "Med"
        
        # 2. Fix Timestamp (extract from original text if "Unknown")
        if data.get("Timestamp") == "Unknown":
            extracted_time = extract_timestamp_from_text(text)
            if extracted_time != "Unknown":
                data["Timestamp"] = extracted_time
        
        # 3. Clean up Timestamp formatting
        timestamp = data.get("Timestamp", "")
        if timestamp and timestamp != "Unknown":
            # Remove extra words
            timestamp = re.sub(r'\b(?:at|around|about|approximately)\s+', '', timestamp, flags=re.IGNORECASE)
            timestamp = timestamp.strip()
            data["Timestamp"] = timestamp
        
        # 4. Ensure Impact_Count is integer
        if "Impact_Count" in data:
            try:
                data["Impact_Count"] = int(data["Impact_Count"])
            except (ValueError, TypeError):
                # Extract number from text as fallback
                numbers = re.findall(r'\d+', text)
                data["Impact_Count"] = int(numbers[0]) if numbers else 0
        
        return data
        
    except Exception as e:
        return {"error": f"Parsing failed: {str(e)}"}

# For backward compatibility
def call_groq_api(text: str) -> dict:
    return call_groq_api_structured(text)

# Test the timestamp extraction
if __name__ == "__main__":
    test_texts = [
        "Database timed out at 6:30 PM. 500 users affected.",
        "API crashed around midnight. 100 users impacted.",
        "Load balancer issue this morning. Some users affected.",
        "Server failure at 2 PM due to overheating.",
    ]
    
    for text in test_texts:
        print(f"\nText: {text}")
        result = call_groq_api_structured(text)
        print(f"Timestamp: {result.get('Timestamp')}")
        print(f"Severity: {result.get('Severity')}")
        print(f"Impact: {result.get('Impact_Count')}")