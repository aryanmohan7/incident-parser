import streamlit as st
import json
from groq_client import call_groq_api_structured

def main():
    st.set_page_config(page_title="Intelligent Incident Parser", page_icon="🛠️")
    
    st.title("🛠️ Intelligent Incident Parser")
    st.markdown("Convert unstructured incident reports to structured JSON using LangChain structured output.")
    
    # Sample data
    sample_text = "Hey team, the production database US-East-I just timed out at 6:30 PM. I think it's the migration script deployed by Sarah. Error code 503 showing up on the load balancer. 500 users affected."
    
    # Load sample button
    if st.button("Load Sample Incident"):
        st.session_state.incident_text = sample_text
    
    # Text input
    incident_text = st.text_area(
        "Incident Report",
        value=st.session_state.get("incident_text", ""),
        height=150,
        placeholder="Paste incident report here..."
    )
    
    # Parse button
    if st.button("🚀 Parse with Structured Output", type="primary"):
        if not incident_text.strip():
            st.warning("Please enter an incident report.")
        else:
            with st.spinner("Parsing with LangChain structured output..."):
                result = call_groq_api_structured(incident_text)
                
                if "error" in result:
                    st.error("❌ Parsing Failed")
                    st.code(result["error"], language="text")
                else:
                    st.success("✅ Success! Structured output:")
                    
                    # Display results
                    cols = st.columns(5)
                    fields = ["Severity", "Component", "Timestamp", "Suspected_Cause", "Impact_Count"]
                    
                    for col, field in zip(cols, fields):
                        with col:
                            st.metric(field, result[field])
                    
                    # Show raw JSON
                    with st.expander("View Raw JSON"):
                        st.json(result)
    
    # Explanation
    with st.sidebar:
        st.markdown("### How It Works")
        st.info("""
        **LangChain Structured Output:**
        1. Defines Pydantic schema
        2. Uses LangChain's PydanticOutputParser
        3. Guarantees valid JSON output
        4. No string manipulation needed
        
        **Benefits:**
        - No more JSON parsing hacks
        - Type-safe output
        - Reliable schema validation
        - Clean, maintainable code
        """)

if __name__ == "__main__":
    if "incident_text" not in st.session_state:
        st.session_state.incident_text = ""
    main()