import os
import re
import json
from typing import Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Try different import strategies
try:
    # Try newer langchain-community first
    from langchain_community.chat_models import ChatGroq
    LANGCHAIN_SOURCE = "community"
except ImportError:
    try:
        # Try older langchain
        from langchain.chat_models import ChatGroq
        LANGCHAIN_SOURCE = "langchain"
    except ImportError:
        # Try langchain-groq
        try:
            from langchain_groq import ChatGroq
            LANGCHAIN_SOURCE = "groq"
        except ImportError:
            LANGCHAIN_SOURCE = None
            print("No LangChain available")

# Import LangChain core components
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import PydanticOutputParser
    LANGCHAIN_CORE_AVAILABLE = True
except ImportError:
    LANGCHAIN_CORE_AVAILABLE = False

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

def call_groq_api_structured(text: str) -> Dict[str, Any]:
    """Main function with fallback strategies."""
    
    # Strategy 1: Try LangChain with ChatGroq
    if LANGCHAIN_SOURCE and LANGCHAIN_CORE_AVAILABLE:
        result = try_langchain_chatgroq(text)
        if "error" not in result:
            return result
    
    # Strategy 2: Try direct Groq API
    result = try_direct_groq_api(text)
    if "error" not in result:
        return result
    
    # Strategy 3: Simple parsing as last resort
    return simple_parse(text)

def try_langchain_chatgroq(text: str) -> Dict[str, Any]:
    """Try using LangChain's ChatGroq."""
    try:
        print(f"Using LangChain source: {LANGCHAIN_SOURCE}")
        
        # Initialize based on source
        if LANGCHAIN_SOURCE == "community":
            llm = ChatGroq(
                temperature=0.1,
                model="llama-3.1-8b-instant",
                groq_api_key=os.getenv("GROQ_API_KEY"),  # Note: groq_api_key, not api_key
                max_tokens=250,
            )
        elif LANGCHAIN_SOURCE == "langchain":
            llm = ChatGroq(
                temperature=0.1,
                model="llama-3.1-8b-instant",
                groq_api_key=os.getenv("GROQ_API_KEY"),
                max_tokens=250,
            )
        else:  # langchain-groq
            llm = ChatGroq(
                temperature=0.1,
                model_name="llama-3.1-8b-instant",  # Note: model_name, not model
                api_key=os.getenv("GROQ_API_KEY"),
                max_tokens=250,
            )
        
        parser = PydanticOutputParser(pydantic_object=IncidentSchema)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an incident data extractor. {format_instructions}"),
            ("user", "Extract data from: {text}")
        ])
        
        chain = prompt | llm | parser
        
        result = chain.invoke({
            "text": text,
            "format_instructions": parser.get_format_instructions()
        })
        
        data = result.dict()
        return post_process_data(data, text)
        
    except Exception as e:
        error_msg = str(e)
        print(f"LangChain failed: {error_msg}")
        
        # If it's the proxies error, try without proxies
        if "proxies" in error_msg:
            return try_direct_groq_api(text)
        
        return {"error": f"LangChain error: {error_msg}"}

def try_direct_groq_api(text: str) -> Dict[str, Any]:
    """Direct Groq API call without LangChain."""
    try:
        from groq import Groq
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        # Create a schema description for the prompt
        schema_desc = """Return JSON with these exact keys:
        - Severity: "High", "Med", or "Low"
        - Component: The affected system
        - Timestamp: Time mentioned or "Unknown"
        - Suspected_Cause: Short phrase
        - Impact_Count: Number (integer)"""
        
        prompt = f"""{schema_desc}

        Incident: {text}

        Example output:
        {{
            "Severity": "High",
            "Component": "Database",
            "Timestamp": "6:30 PM",
            "Suspected_Cause": "Migration script",
            "Impact_Count": 500
        }}"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=250,
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        result = clean_json_response(result)
        
        data = json.loads(result)
        return post_process_data(data, text)
        
    except Exception as e:
        print(f"Direct API failed: {e}")
        return {"error": f"Direct API failed: {str(e)}"}

def simple_parse(text: str) -> Dict[str, Any]:
    """Simple parsing as last resort."""
    print("Using simple parse fallback")
    
    # Extract basic information with regex
    data = {
        "Severity": "Med",
        "Component": "Unknown",
        "Timestamp": "Unknown",
        "Suspected_Cause": "Unknown",
        "Impact_Count": 0
    }
    
    # Extract numbers for Impact_Count
    numbers = re.findall(r'\d+', text)
    if numbers:
        data["Impact_Count"] = int(numbers[0])
        if data["Impact_Count"] >= 500:
            data["Severity"] = "High"
        elif data["Impact_Count"] >= 100:
            data["Severity"] = "Med"
        else:
            data["Severity"] = "Low"
    
    # Extract time
    time_pattern = r'(\d{1,2}:\d{2}\s*[AP]M|\d{1,2}\s*[AP]M)'
    match = re.search(time_pattern, text, re.IGNORECASE)
    if match:
        data["Timestamp"] = match.group(1).upper()
    
    # Guess component
    if "database" in text.lower():
        data["Component"] = "Database"
    elif "api" in text.lower():
        data["Component"] = "API"
    elif "load balancer" in text.lower():
        data["Component"] = "Load Balancer"
    elif "server" in text.lower():
        data["Component"] = "Server"
    
    # Add metadata
    data["_metadata"] = {
        "parsing_method": "simple_regex",
        "original_text_length": len(text)
    }
    
    return data

def clean_json_response(response: str) -> str:
    """Clean JSON response."""
    response = response.replace('```json', '').replace('```', '').strip()
    
    # Find JSON object
    start = response.find('{')
    end = response.rfind('}') + 1
    
    if start != -1 and end != 0:
        return response[start:end]
    
    return response

def post_process_data(data: Dict[str, Any], original_text: str) -> Dict[str, Any]:
    """Post-process and validate data."""
    # Ensure all fields exist
    required = ["Severity", "Component", "Timestamp", "Suspected_Cause", "Impact_Count"]
    for field in required:
        if field not in data:
            data[field] = "Unknown" if field != "Impact_Count" else 0
    
    # Fix Severity based on impact
    impact = data.get("Impact_Count", 0)
    if isinstance(impact, str):
        numbers = re.findall(r'\d+', impact)
        impact = int(numbers[0]) if numbers else 0
        data["Impact_Count"] = impact
    
    if impact >= 500:
        data["Severity"] = "High"
    elif impact >= 100 and data.get("Severity") == "Low":
        data["Severity"] = "Med"
    elif impact < 100 and data.get("Severity") == "High":
        data["Severity"] = "Med"
    
    # Ensure Severity is valid
    if data["Severity"] not in ["High", "Med", "Low"]:
        data["Severity"] = "Med"
    
    return data

# Backward compatibility
def call_groq_api(text: str) -> Dict[str, Any]:
    return call_groq_api_structured(text)

if __name__ == "__main__":
    # Test
    test_text = "Database timed out at 6:30 PM. 500 users affected."
    result = call_groq_api_structured(test_text)
    print(f"Test result: {result}")