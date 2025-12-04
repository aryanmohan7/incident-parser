import os
import sys

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from groq_client import call_groq_api, load_prompt_template
from json_utils import parse_and_validate
import json

print("🧪 Testing Prompt Loading...")
prompt_template = load_prompt_template()
print(f"Prompt template length: {len(prompt_template)} chars")
print(f"Contains '{{text}}' placeholder: {'{text}' in prompt_template}")
print(f"First 200 chars: {prompt_template[:200]}...\n")

print("🧪 Testing API Call...\n")

test_cases = [
    "Hey team, the production database US-East-I just timed out at 6:30 PM. I think it's the migration script deployed by Sarah. Error code 503 showing up on the load balancer. 500 users affected.",
    "API server crashed around midnight. Memory leak suspected. 1000 users impacted.",
]

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*60}")
    print(f"Test {i}:")
    print(f"Input: {test[:80]}...")
    print(f"{'='*60}")
    
    try:
        print("Calling Groq API...")
        raw = call_groq_api(test)
        print(f"✓ Raw API response received ({len(raw)} chars)")
        print(f"Raw preview: {raw[:150]}...")
        
        print("\nParsing response...")
        result = parse_and_validate(raw)
        
        if "error" in result:
            print(f"✗ Error: {result['error']}")
            if "raw_response" in result:
                print(f"Raw response: {result['raw_response'][:200]}...")
        else:
            print("✅ Success! Parsed data:")
            print(json.dumps(result, indent=2))
            
    except Exception as e:
        print(f"✗ Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("Debug complete!")