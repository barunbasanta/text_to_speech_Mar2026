import asyncio
import tempfile
from pathlib import Path

import streamlit as st

try:
    import edge_tts
except ImportError:
    edge_tts = None

st.set_page_config(page_title="Text to Speech Generator", page_icon="🔊", layout="centered")

st.title("🔊 Text to Speech Generator")
st.write("Enter text, pick a language and voice, then generate speech as an MP3 file.")

VOICE_OPTIONS = {
    "English (US)": {
        "en-US-JennyNeural": "English (US) — Jenny — Female",
        "en-US-GuyNeural": "English (US) — Guy — Male",
        "en-US-AriaNeural": "English (US) — Aria — Female",
    },
    "Bengali (India)": {
        "bn-IN-BashkarNeural": "Bengali (India) — Bashkar — Male",
        "bn-IN-TanishaaNeural": "Bengali (India) — Tanishaa — Female",
    },
    "Bengali (Bangladesh)": {
        "bn-BD-PradeepNeural": "Bengali (Bangladesh) — Pradeep — Male",
        "bn-BD-NabanitaNeural": "Bengali (Bangladesh) — Nabanita — Female",
    },
    "Hindi": {
        "hi-IN-MadhurNeural": "Hindi — Madhur — Male",
        "hi-IN-SwaraNeural": "Hindi — Swara — Female",
    },
    "Spanish": {
        "es-ES-AlvaroNeural": "Spanish — Alvaro — Male",
        "es-ES-ElviraNeural": "Spanish — Elvira — Female",
    },
    "French": {
        "fr-FR-HenriNeural": "French — Henri — Male",
        "fr-FR-DeniseNeural": "French — Denise — Female",
    },
    "German": {
        "de-DE-ConradNeural": "German — Conrad — Male",
        "de-DE-KatjaNeural": "German — Katja — Female",
    },
    "Italian": {
        "it-IT-DiegoNeural": "Italian — Diego — Male",
        "it-IT-ElsaNeural": "Italian — Elsa — Female",
    },
    "Portuguese (Brazil)": {
        "pt-BR-AntonioNeural": "Portuguese (Brazil) — Antonio — Male",
        "pt-BR-FranciscaNeural": "Portuguese (Brazil) — Francisca — Female",
    },
}

VOICE_STYLE_HINTS = {
    "bn-IN-BashkarNeural": "Closest built-in option to a Bengali adult male narrator.",
    "bn-BD-PradeepNeural": "Closest built-in option to a Bangla adult male narrator.",
    "bn-IN-TanishaaNeural": "Bengali female voice with a clear narration style.",
    "bn-BD-NabanitaNeural": "Bangla female voice with a warm narration style.",
}

STYLE_PRESETS = {
    "Natural": {"rate": 0, "pitch": 0, "label": "Balanced everyday speech"},
    "Deep Male Narrator": {"rate": -10, "pitch": -15, "label": "Lower and steadier delivery"},
    "Warm Storyteller": {"rate": -12, "pitch": -5, "label": "Gentle story-reading tone"},
    "Kid Friendly": {"rate": 5, "pitch": 10, "label": "Lighter, more playful tone"},
    "Cartoon": {"rate": 10, "pitch": 18, "label": "Animated and expressive"},
    "Calm Teacher": {"rate": -8, "pitch": 0, "label": "Clear and patient delivery"},
    "News Reader": {"rate": -2, "pitch": -3, "label": "Neutral and formal"},
    "Bengali Man ~40": {"rate": -10, "pitch": -15, "label": "Closest preset for a mature Bengali male voice"},
}


def sanitize_filename(name: str) -> str:
    name = name.strip() or "speech.mp3"
    if not name.lower().endswith(".mp3"):
        name += ".mp3"
    safe = "".join(c for c in name if c.isalnum() or c in ("-", "_", ".", " ")).strip()
    return safe or "speech.mp3"


async def synthesize_to_file(text: str, voice: str, rate: str, pitch: str, output_path: str) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


# Initialize state so the voice list updates correctly when language changes
if "language_group" not in st.session_state:
    st.session_state.language_group = list(VOICE_OPTIONS.keys())[0]

current_language = st.session_state.language_group
current_voice_options = VOICE_OPTIONS[current_language]

if "selected_voice" not in st.session_state or st.session_state.selected_voice not in current_voice_options:
    st.session_state.selected_voice = list(current_voice_options.keys())[0]


def sync_voice_with_language() -> None:
    language = st.session_state.language_group
    valid_voices = VOICE_OPTIONS[language]
    if st.session_state.selected_voice not in valid_voices:
        st.session_state.selected_voice = list(valid_voices.keys())[0]


with st.form("tts_form"):
    text = st.text_area(
        "Enter text",
        value="",
        height=180,
        placeholder="Type or paste text here...",
    )

    st.selectbox(
        "Language",
        options=list(VOICE_OPTIONS.keys()),
        key="language_group",
        on_change=sync_voice_with_language,
    )

    voice_map = VOICE_OPTIONS[st.session_state.language_group]
    selected_voice = st.selectbox(
        "Voice",
        options=list(voice_map.keys()),
        format_func=lambda x: voice_map[x],
        key="selected_voice",
    )

    style_preset = st.selectbox("Style preset", list(STYLE_PRESETS.keys()), index=0)
    preset = STYLE_PRESETS[style_preset]
    st.caption(f"Preset: {preset['label']}")

    use_custom_controls = st.checkbox("Fine-tune speed and pitch manually", value=False)

    if use_custom_controls:
        rate_percent = st.slider("Speech speed", min_value=-50, max_value=50, value=preset["rate"], step=5)
        pitch_hz = st.slider("Pitch", min_value=-50, max_value=50, value=preset["pitch"], step=5)
    else:
        rate_percent = preset["rate"]
        pitch_hz = preset["pitch"]

    filename = st.text_input("Output filename", value="speech.mp3")
    submitted = st.form_submit_button("Generate Speech")

if submitted:
    cleaned_text = text.strip()

    if edge_tts is None:
        st.error("Missing dependency: edge-tts. Install it with: pip install edge-tts")
    elif not cleaned_text:
        st.error("Please enter some text first.")
    else:
        tmp_path = None
        try:
            rate = f"{rate_percent:+d}%"
            pitch = f"{pitch_hz:+d}Hz"

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_path = tmp_file.name

            asyncio.run(synthesize_to_file(cleaned_text, selected_voice, rate, pitch, tmp_path))

            audio_bytes = Path(tmp_path).read_bytes()

            st.success("Speech generated successfully.")
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button(
                label="Download MP3",
                data=audio_bytes,
                file_name=sanitize_filename(filename),
                mime="audio/mpeg",
            )
        except Exception as e:
            st.error("Could not generate speech.")
            st.exception(e)
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass
