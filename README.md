# Streamlit Text-to-Speech App

This app converts text into speech and lets users download the result as an MP3.

## Features
- Text to speech
- Bengali (India and Bangladesh) voices
- English, Hindi, Spanish, French, German, Italian, Portuguese
- Voice selection
- Style presets including `Bengali Man ~40`
- Optional manual speed and pitch controls

## Files
- `app.py` - main Streamlit app
- `requirements.txt` - Python dependencies

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud
Use:
- Main file path: `app.py`

## Notes
- This app uses `edge-tts`, so it needs internet access when generating speech.
- Exact age-specific voices like `40-year-old Bengali man` are not exposed directly by standard TTS providers. The preset approximates that style using a Bengali male neural voice plus tuned speed and pitch.
