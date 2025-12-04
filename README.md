# 🛠️ Intelligent Incident Parser

A lightweight web application that converts unstructured incident reports into structured JSON using Groq API.

## Features
- Extracts 5 key fields from messy incident text
- Validates output with Pydantic schema
- Clean, responsive Streamlit UI
- Robust error handling
- Modular architecture

## Quick Start
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Add your Groq API key to `.env` file
4. Run: `streamlit run app.py`

## Architecture
- `app.py` - Main Streamlit application
- `groq_client.py` - Groq API interactions
- `json_utils.py` - JSON parsing and validation
- `prompt.txt` - AI prompt template

## Demo Video
https://www.loom.com/share/56c9a70a8b9a41deb594bfe72989fdc8