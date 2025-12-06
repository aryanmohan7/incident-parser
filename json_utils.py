from typing import Dict, Any
from groq_client import call_groq_api_structured

def extract_incident_data(text: str, api_call_func=None) -> Dict[str, Any]:
    """Extract incident data - simple wrapper."""
    if not text or not text.strip():
        return {"error": "Input text is empty"}
    
    # Use structured parser (with LangChain)
    return call_groq_api_structured(text)