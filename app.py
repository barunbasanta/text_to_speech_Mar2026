import asyncio
import re
import tempfile
from pathlib import Path
import streamlit as st

try:
    import edge_tts
except ImportError:
    edge_tts = None

st.set_page_config(page_title="Text to Speech Generator", page_icon="🔊", layout="centered")

st.title("🔊 Text to Speech Generator")

st.markdown("""
Enter text and generate speech.

**Pause Feature:**
- Use format: `Pause X sec`
- Example: `Pause 35 sec`
- Max allowed: 600 sec
- Automatically inserts silence in speech
""")

VOICE_OPTIONS = {
    "English (US)": {
        "Male": "en-US-GuyNeural",
        "Female": "en-US-JennyNeural",
        "Boy": "en-US-AndrewMultilingualNeural",
        "Girl": "en-US-EmmaMultilingualNeural",
    },
    "Bengali (India)": {
        "Male": "bn-IN-BashkarNeural",
        "Female": "bn-IN-TanishaaNeural",
        "Boy": "bn-IN-BashkarNeural",
        "Girl": "bn-IN-TanishaaNeural",
    },
}

def convert_pause_to_ssml(text):
    pattern = re.compile(r'Pause (\d+) sec', re.IGNORECASE)

    def repl(match):
        sec = min(int(match.group(1)), 600)
        return f'<break time="{sec}s"/>'

    return pattern.sub(repl, text)

async def synthesize(text, voice, path):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice
    )
    await communicate.save(path)

language = st.selectbox("Language", list(VOICE_OPTIONS.keys()))
voice_type = st.selectbox("Voice", list(VOICE_OPTIONS[language].keys()))
text = st.text_area("Enter text", "")

if st.button("Generate Speech"):
    if not text.strip():
        st.error("Enter text")
    else:
        try:
            processed_text = convert_pause_to_ssml(text)

            # Wrap in SSML
            ssml_text = f"<speak>{processed_text}</speak>"

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

            asyncio.run(synthesize(ssml_text, VOICE_OPTIONS[language][voice_type], tmp))

            audio = Path(tmp).read_bytes()

            st.success("Speech generated successfully.")
            st.audio(audio)
            st.download_button("Download", audio, "speech.mp3")

        except Exception as e:
            st.error("Error generating speech")
            st.exception(e)
