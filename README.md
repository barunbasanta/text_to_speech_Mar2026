# Streamlit Text-to-Speech App

Run locally:
```bash
pip install -r requirements.txt
streamlit run app.py
```

Notes:
- No pydub dependency
- No ffmpeg dependency
- Mixed-language segments are combined with pure Python MP3 byte concatenation
