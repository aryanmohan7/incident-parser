import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def load_prompt_template() -> str:
    """Load prompt template from file."""
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            content = f.read()
            return content
    except FileNotFoundError:
        # Fallback prompt
        return """Extract the following fields from this incident report and return ONLY JSON:

Fields to extract:
1. Severity: Must be exactly "High", "Med", or "Low" based on impact
2. Component: The affected system component
3. Timestamp: Time mentioned or "Unknown"
4. Suspected_Cause: Short phrase describing likely cause
5. Impact_Count: Number of users affected (integer)

INCIDENT REPORT: {text}

RETURN ONLY THIS JSON FORMAT (no other text):
{{
    "Severity": "High",
    "Component": "Database",
    "Timestamp": "6:30 PM",
    "Suspected_Cause": "Migration script failure",
    "Impact_Count": 500
}}

Important rules:
- Impact_Count must be a number, not text
- Severity must be "High", "Med", or "Low" only
- Return ONLY the JSON object, no explanations"""

def call_groq_api(text: str) -> str:
    """Call Groq API to extract structured data from incident text."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # Load and format prompt
    prompt_template = load_prompt_template()
    
    # Debug: Check what's in the template
    print(f"DEBUG: Prompt template contains '{{text}}': {'{text}' in prompt_template}")
    
    # Format the prompt with the incident text
    try:
        prompt = prompt_template.format(text=text)
    except KeyError as e:
        print(f"ERROR: Could not format prompt. Missing key: {e}")
        print(f"Prompt template: {prompt_template[:200]}...")
        # Use a simple fallback
        prompt = f"""Extract incident data from: "{text}"

Return JSON with: Severity, Component, Timestamp, Suspected_Cause, Impact_Count"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Fast and reliable
            messages=[
                {
                    "role": "system", 
                    "content": "You are a JSON data extractor. Always return ONLY valid JSON, no other text."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"}  # Force JSON output
        )
        result = response.choices[0].message.content.strip()
        
        # Clean up the response
        result = result.replace('```json', '').replace('```', '').strip()
        return result
        
    except Exception as e:
        error_msg = str(e)
        # Handle specific API errors
        if "model_decommissioned" in error_msg:
            return '{"error": "Model is deprecated. Please update model name."}'
        return f'{{"error": "API call failed: {error_msg}"}}'