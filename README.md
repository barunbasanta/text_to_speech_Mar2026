# Streamlit Text-to-Speech App

Run locally:
```bash
pip install -r requirements.txt
streamlit run app.py
```

Notes:
- This version does not use pydub.
- It concatenates mixed-language audio segments with ffmpeg, which is already present on Streamlit Community Cloud.
