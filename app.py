import asyncio
import re
import tempfile
from pathlib import Path

import streamlit as st
from pydub import AudioSegment

try:
    import edge_tts
except ImportError:
    edge_tts = None

st.set_page_config(page_title="Text to Speech Generator", page_icon="🔊", layout="centered")

st.title("🔊 Text to Speech Generator")
st.write("Enter text, pick a language and voice, then generate speech as an MP3 file.")

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
    "Bengali (Bangladesh)": {
        "Male": "bn-BD-PradeepNeural",
        "Female": "bn-BD-NabanitaNeural",
        "Boy": "bn-BD-PradeepNeural",
        "Girl": "bn-BD-NabanitaNeural",
    },
    "Hindi": {
        "Male": "hi-IN-MadhurNeural",
        "Female": "hi-IN-SwaraNeural",
        "Boy": "hi-IN-MadhurNeural",
        "Girl": "hi-IN-SwaraNeural",
    },
    "Spanish": {
        "Male": "es-ES-AlvaroNeural",
        "Female": "es-ES-ElviraNeural",
        "Boy": "es-ES-AlvaroNeural",
        "Girl": "es-ES-ElviraNeural",
    },
    "French": {
        "Male": "fr-FR-HenriNeural",
        "Female": "fr-FR-DeniseNeural",
        "Boy": "fr-FR-HenriNeural",
        "Girl": "fr-FR-DeniseNeural",
    },
    "German": {
        "Male": "de-DE-ConradNeural",
        "Female": "de-DE-KatjaNeural",
        "Boy": "de-DE-ConradNeural",
        "Girl": "de-DE-KatjaNeural",
    },
    "Italian": {
        "Male": "it-IT-DiegoNeural",
        "Female": "it-IT-ElsaNeural",
        "Boy": "it-IT-DiegoNeural",
        "Girl": "it-IT-ElsaNeural",
    },
    "Portuguese (Brazil)": {
        "Male": "pt-BR-AntonioNeural",
        "Female": "pt-BR-FranciscaNeural",
        "Boy": "pt-BR-AntonioNeural",
        "Girl": "pt-BR-FranciscaNeural",
    },
}

STYLE_PRESETS_BY_VOICE = {
    "Male": {
        "Natural": {"rate": 0, "pitch": 0, "label": "Balanced everyday speech"},
        "Deep Narrator": {"rate": -10, "pitch": -15, "label": "Lower and steadier delivery"},
        "Warm Storyteller": {"rate": -12, "pitch": -5, "label": "Gentle story-reading tone"},
        "Calm Teacher": {"rate": -8, "pitch": 0, "label": "Clear and patient delivery"},
        "News Reader": {"rate": -2, "pitch": -3, "label": "Neutral and formal"},
        "Cartoon": {"rate": 10, "pitch": 12, "label": "Animated and expressive"},
    },
    "Female": {
        "Natural": {"rate": 0, "pitch": 0, "label": "Balanced everyday speech"},
        "Warm Storyteller": {"rate": -10, "pitch": 4, "label": "Gentle story-reading tone"},
        "Calm Teacher": {"rate": -8, "pitch": 2, "label": "Clear and patient delivery"},
        "News Reader": {"rate": -2, "pitch": 1, "label": "Neutral and formal"},
        "Cartoon": {"rate": 10, "pitch": 16, "label": "Animated and expressive"},
        "Kid Friendly": {"rate": 6, "pitch": 10, "label": "Lighter, playful delivery"},
    },
    "Boy": {
        "Natural": {"rate": 6, "pitch": 8, "label": "Balanced child-like speech"},
        "Kid Friendly": {"rate": 10, "pitch": 14, "label": "Playful and bright"},
        "Cartoon": {"rate": 14, "pitch": 20, "label": "Animated and expressive"},
        "Excited": {"rate": 12, "pitch": 16, "label": "Energetic child-like delivery"},
        "Story Friend": {"rate": 4, "pitch": 10, "label": "Friendly storytelling tone"},
    },
    "Girl": {
        "Natural": {"rate": 6, "pitch": 10, "label": "Balanced child-like speech"},
        "Kid Friendly": {"rate": 10, "pitch": 16, "label": "Playful and bright"},
        "Cartoon": {"rate": 14, "pitch": 22, "label": "Animated and expressive"},
        "Excited": {"rate": 12, "pitch": 18, "label": "Energetic child-like delivery"},
        "Story Friend": {"rate": 4, "pitch": 12, "label": "Friendly storytelling tone"},
    },
}

BENGALI_LANGUAGES = {"Bengali (India)", "Bengali (Bangladesh)"}


def sanitize_filename(name: str) -> str:
    name = name.strip() or "speech.mp3"
    if not name.lower().endswith(".mp3"):
        name += ".mp3"
    safe = "".join(c for c in name if c.isalnum() or c in ("-", "_", ".", " ")).strip()
    return safe or "speech.mp3"


async def synthesize_to_file(text: str, voice: str, rate: str, pitch: str, output_path: str) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


def contains_bengali_char(text: str) -> bool:
    return any("\u0980" <= ch <= "\u09FF" for ch in text)


def contains_english_char(text: str) -> bool:
    return any(("A" <= ch <= "Z") or ("a" <= ch <= "z") for ch in text)


def classify_char(ch: str) -> str:
    if "\u0980" <= ch <= "\u09FF":
        return "bn"
    if ("A" <= ch <= "Z") or ("a" <= ch <= "z") or ("0" <= ch <= "9"):
        return "en"
    if ch.isspace():
        return "space"
    return "other"


def split_mixed_bengali_english(text: str) -> list[tuple[str, str]]:
    if not text:
        return []

    raw_segments = []
    current_type = classify_char(text[0])
    current_text = text[0]

    for ch in text[1:]:
        ch_type = classify_char(ch)
        if ch_type == current_type:
            current_text += ch
        else:
            raw_segments.append((current_type, current_text))
            current_type = ch_type
            current_text = ch

    raw_segments.append((current_type, current_text))

    merged = []
    for seg_type, seg_text in raw_segments:
        if seg_type in {"space", "other"} and merged:
            prev_type, prev_text = merged[-1]
            merged[-1] = (prev_type, prev_text + seg_text)
        else:
            merged.append((seg_type, seg_text))

    cleaned = [(seg_type, seg_text.strip()) for seg_type, seg_text in merged if seg_text.strip()]
    return cleaned


def should_use_mixed_logic(language_group: str, text: str) -> bool:
    return (
        language_group in BENGALI_LANGUAGES
        and contains_bengali_char(text)
        and contains_english_char(text)
    )


def english_voice_for_category(voice_category: str) -> str:
    return VOICE_OPTIONS["English (US)"][voice_category]


async def synthesize_mixed_text_to_file(
    text: str,
    language_group: str,
    voice_category: str,
    rate: str,
    pitch: str,
    output_path: str,
) -> None:
    base_voice = VOICE_OPTIONS[language_group][voice_category]
    english_voice = english_voice_for_category(voice_category)
    segments = split_mixed_bengali_english(text)

    if not segments:
        await synthesize_to_file(text, base_voice, rate, pitch, output_path)
        return

    audio = AudioSegment.silent(duration=0)
    temp_files = []

    try:
        for seg_type, seg_text in segments:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                seg_path = tmp_file.name

            temp_files.append(seg_path)

            voice = english_voice if seg_type == "en" else base_voice
            await synthesize_to_file(seg_text, voice, rate, pitch, seg_path)
            audio += AudioSegment.from_file(seg_path, format="mp3")

        audio.export(output_path, format="mp3")
    finally:
        for seg_path in temp_files:
            try:
                Path(seg_path).unlink(missing_ok=True)
            except Exception:
                pass


if "language_group" not in st.session_state:
    st.session_state.language_group = "English (US)"

current_categories = VOICE_OPTIONS[st.session_state.language_group]
if "voice_category" not in st.session_state or st.session_state.voice_category not in current_categories:
    st.session_state.voice_category = list(current_categories.keys())[0]

current_presets = STYLE_PRESETS_BY_VOICE[st.session_state.voice_category]
if "style_preset" not in st.session_state or st.session_state.style_preset not in current_presets:
    st.session_state.style_preset = list(current_presets.keys())[0]

if "use_custom_controls" not in st.session_state:
    st.session_state.use_custom_controls = False


def language_changed() -> None:
    categories = VOICE_OPTIONS[st.session_state.language_group]
    if st.session_state.voice_category not in categories:
        st.session_state.voice_category = list(categories.keys())[0]
    voice_changed()


def voice_changed() -> None:
    presets = STYLE_PRESETS_BY_VOICE[st.session_state.voice_category]
    if st.session_state.style_preset not in presets:
        st.session_state.style_preset = list(presets.keys())[0]


st.selectbox(
    "Language",
    options=list(VOICE_OPTIONS.keys()),
    key="language_group",
    on_change=language_changed,
)

voice_categories = list(VOICE_OPTIONS[st.session_state.language_group].keys())
st.selectbox(
    "Voice",
    options=voice_categories,
    key="voice_category",
    on_change=voice_changed,
)

style_options = list(STYLE_PRESETS_BY_VOICE[st.session_state.voice_category].keys())
st.selectbox(
    "Style preset",
    options=style_options,
    key="style_preset",
)

preset = STYLE_PRESETS_BY_VOICE[st.session_state.voice_category][st.session_state.style_preset]
st.caption(f"Preset: {preset['label']}")

st.checkbox(
    "Fine-tune speed and pitch manually",
    key="use_custom_controls",
)

default_rate = preset["rate"]
default_pitch = preset["pitch"]

if (
    "rate_percent" not in st.session_state
    or not st.session_state.use_custom_controls
):
    st.session_state.rate_percent = default_rate

if (
    "pitch_hz" not in st.session_state
    or not st.session_state.use_custom_controls
):
    st.session_state.pitch_hz = default_pitch

if st.session_state.use_custom_controls:
    rate_percent = st.slider(
        "Speech speed",
        min_value=-50,
        max_value=50,
        value=st.session_state.rate_percent,
        step=5,
        key="rate_percent",
    )
    pitch_hz = st.slider(
        "Pitch",
        min_value=-50,
        max_value=50,
        value=st.session_state.pitch_hz,
        step=5,
        key="pitch_hz",
    )
else:
    rate_percent = default_rate
    pitch_hz = default_pitch

with st.form("tts_form"):
    text = st.text_area(
        "Enter text",
        value="",
        height=180,
        placeholder="Type or paste text here...",
    )
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

            if should_use_mixed_logic(st.session_state.language_group, cleaned_text):
                asyncio.run(
                    synthesize_mixed_text_to_file(
                        cleaned_text,
                        st.session_state.language_group,
                        st.session_state.voice_category,
                        rate,
                        pitch,
                        tmp_path,
                    )
                )
            else:
                selected_voice_id = VOICE_OPTIONS[st.session_state.language_group][st.session_state.voice_category]
                asyncio.run(
                    synthesize_to_file(
                        cleaned_text,
                        selected_voice_id,
                        rate,
                        pitch,
                        tmp_path,
                    )
                )

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
