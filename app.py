import streamlit as st
from groq_client import call_groq_api
from json_utils import extract_incident_data

def main():
    st.set_page_config(page_title="Intelligent Incident Parser", page_icon="🛠️")
    
    st.title("🛠️ Intelligent Incident Parser")
    st.markdown("Paste an incident report below to extract structured data.")
    
    # Sample data for easy testing
    sample_text = "Hey team, the production database US-East-I just timed out at 6:30 PM. I think it's the migration script deployed by Sarah. Error code 503 showing up on the load balancer. 500 users affected."
    
    # Add a button to load sample
    if st.button("Load Sample Incident"):
        st.session_state.incident_text = sample_text
    
    # Text area for input
    incident_text = st.text_area(
        "Incident Report", 
        value=st.session_state.get("incident_text", ""),
        height=150,
        placeholder="Paste your incident report here..."
    )
    
    # Parse button
    if st.button("🚀 Parse Incident", type="primary"):
        if not incident_text.strip():
            st.warning("Please enter an incident report first.")
        else:
            with st.spinner("Parsing with AI..."):
                # Pass the API function as a parameter
                result = extract_incident_data(incident_text, call_groq_api)
                
                if "error" in result:
                    st.error("❌ Parsing Failed")
                    st.code(result["error"], language="text")
                    
                    if "raw_response" in result:
                        with st.expander("View Raw AI Response"):
                            st.code(result["raw_response"], language="json")
                else:
                    st.success("✅ Incident Parsed Successfully!")
                    
                    # Display results in a nice format
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Severity", result["Severity"])
                        st.metric("Component", result["Component"])
                    
                    with col2:
                        st.metric("Timestamp", result["Timestamp"])
                        st.metric("Users Affected", result["Impact_Count"])
                    
                    st.markdown("**Suspected Cause:**")
                    st.info(result["Suspected_Cause"])
                    
                    # Show raw JSON
                    with st.expander("View Raw JSON"):
                        st.json(result)
    
    # Explanation section
    with st.expander("ℹ️ How it works"):
        st.markdown("""
        1. **Input**: User provides unstructured incident report text
        2. **AI Processing**: Groq API extracts structured data using prompt engineering
        3. **Validation**: Pydantic validates the JSON schema
        4. **Output**: Clean, structured data ready for database entry
        
        **Fields extracted**:
        - Severity (High/Med/Low)
        - Component
        - Timestamp
        - Suspected_Cause
        - Impact_Count
        """)
    
    # Footer
    st.markdown("---")
    st.caption("Built with Groq API • Streamlit • Pydantic | SafeAI Challenge")

if __name__ == "__main__":
    main()