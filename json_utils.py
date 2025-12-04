import json
import re
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, Optional
from groq_client import call_groq_api_structured

# Define Pydantic model for validation
class Incident(BaseModel):
    Severity: str
    Component: str
    Timestamp: str
    Suspected_Cause: str
    Impact_Count: int

def clean_json_response(raw_response: str) -> Optional[str]:
    """Clean and extract JSON from raw response."""
    if not raw_response:
        return None
    
    # Remove markdown code blocks
    raw_response = raw_response.replace('```json', '').replace('```', '').strip()
    
    # Try direct JSON parsing first
    try:
        json.loads(raw_response)
        return raw_response
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON in the text
    try:
        # Look for content between curly braces
        start = raw_response.find('{')
        end = raw_response.rfind('}') + 1
        
        if start != -1 and end != 0:
            json_str = raw_response[start:end]
            json.loads(json_str)
            return json_str
    except:
        pass
    
    # Try regex extraction
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, raw_response, re.DOTALL)
    
    for match in matches:
        try:
            json.loads(match)
            return match
        except:
            continue
    
    return None

def parse_and_validate(raw_response: str) -> Dict[str, Any]:
    """Parse JSON response and validate against schema."""
    # Check if API call failed
    if "error" in raw_response and "API call failed" in raw_response:
        return {"error": raw_response, "raw_response": raw_response}
    
    # Clean and extract JSON
    json_str = clean_json_response(raw_response)
    
    if not json_str:
        return {"error": "No valid JSON found in response", "raw_response": raw_response}
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return {"error": f"JSON decode failed: {str(e)}", "raw_response": raw_response}
    
    # Validate with Pydantic
    try:
        # Ensure all required fields exist
        required_fields = ["Severity", "Component", "Timestamp", "Suspected_Cause", "Impact_Count"]
        for field in required_fields:
            if field not in data:
                data[field] = "Unknown" if field != "Impact_Count" else 0
        
        # Convert Impact_Count to int if possible
        if "Impact_Count" in data:
            try:
                if isinstance(data["Impact_Count"], str):
                    # Extract numbers from string
                    numbers = re.findall(r'\d+', data["Impact_Count"])
                    data["Impact_Count"] = int(numbers[0]) if numbers else 0
                else:
                    data["Impact_Count"] = int(data["Impact_Count"])
            except:
                data["Impact_Count"] = 0
        
        validated = Incident(**data)
        return validated.dict()
        
    except ValidationError as e:
        return {"error": f"Validation failed: {str(e)}", "raw_response": raw_response, "data": data}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}", "raw_response": raw_response}

def extract_incident_data(text: str, api_call_func=None) -> Dict[str, Any]:
    """Extract incident data using structured output formatter."""
    if not text or not text.strip():
        return {"error": "Input text is empty"}
    
    # Use structured parser directly
    return call_groq_api_structured(text)