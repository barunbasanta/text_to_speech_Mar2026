
import asyncio
import re
import tempfile
from pathlib import Path
import streamlit as st

import edge_tts

st.set_page_config(page_title="Text to Speech Generator", page_icon="🔊")

st.title("🔊 Text to Speech Generator")

st.markdown("""
**Pause Usage:**
Type `Pause X sec` anywhere in text (e.g., `Pause 20 sec`).
The app will pause speech for X seconds (max 600 sec).
""")

VOICE_OPTIONS = {
    "English (US)": {
        "Male": "en-US-GuyNeural",
        "Female": "en-US-JennyNeural",
    },
    "Bengali (India)": {
        "Male": "bn-IN-BashkarNeural",
        "Female": "bn-IN-TanishaaNeural",
    },
}

def split_text(text):
    pattern = re.compile(r'Pause (\d+) sec', re.IGNORECASE)
    parts=[]
    last=0
    for m in pattern.finditer(text):
        if m.start()>last:
            parts.append(("text", text[last:m.start()]))
        sec=min(int(m.group(1)),600)
        parts.append(("pause", sec))
        last=m.end()
    if last<len(text):
        parts.append(("text", text[last:]))
    return parts

async def tts(text, voice, path):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(path)

async def generate_pause(sec, voice, path):
    # create approximate silence using slow minimal speech
    chunks = []
    tmp_files=[]
    try:
        for _ in range(sec):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
            await tts(".", voice, tmp)  # tiny sound
            tmp_files.append(tmp)
        with open(path,"wb") as out:
            for f in tmp_files:
                out.write(Path(f).read_bytes())
    finally:
        for f in tmp_files:
            Path(f).unlink(missing_ok=True)

language = st.selectbox("Language", list(VOICE_OPTIONS.keys()))
voice_type = st.selectbox("Voice", list(VOICE_OPTIONS[language].keys()))
text = st.text_area("Enter text","")

if st.button("Generate Speech"):
    if not text.strip():
        st.error("Enter text")
    else:
        parts = split_text(text)
        files=[]
        try:
            for typ,val in parts:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                if typ=="text":
                    asyncio.run(tts(val, VOICE_OPTIONS[language][voice_type], tmp))
                else:
                    asyncio.run(generate_pause(val, VOICE_OPTIONS[language][voice_type], tmp))
                files.append(tmp)

            final = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
            with open(final,"wb") as out:
                for f in files:
                    out.write(Path(f).read_bytes())

            audio = Path(final).read_bytes()
            st.audio(audio)
            st.download_button("Download", audio, "speech.mp3")

        finally:
            for f in files:
                Path(f).unlink(missing_ok=True)
