from __future__ import annotations
import os
import re
import base64
import traceback
import requests
import gradio as gr
import pandas as pd

from config import settings
from agents import Orchestrator

# OpenAI client (Images + STT + TTS)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

orch = Orchestrator()
oa_client = OpenAI(api_key=settings.OPENAI_API_KEY) if (OpenAI and settings.OPENAI_API_KEY) else None

# ---------- Constants ----------
LANG_CHOICES = [
    ("English", "en"),
    ("German", "de"),
    ("French", "fr"),
    ("Spanish", "es"),
    ("Italian", "it"),
]
IMG_DIR = os.path.join(os.getcwd(), "generated_images")
AUDIO_DIR = os.path.join(os.getcwd(), "generated_audio")
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# ---------- Utils ----------
def _safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", (s or "")).strip("_") or "city"

def generate_city_image_1024(city_hint: str) -> str | None:
    """Generate a 1024x1024 city image via DALL·E 3 (b64 or URL response)."""
    if not (oa_client and settings.OPENAI_API_KEY):
        print("[image] OpenAI client yok ya da API key eksik.")
        return None

    model_name = getattr(settings, "IMAGE_MODEL", "dall-e-3")
    prompt = (
        f"A high-quality 1024x1024 photorealistic wide cityscape of {city_hint}, "
        f"with iconic landmarks and golden-hour lighting."
    )
    print(f"[image] trying model: {model_name}")

    try:
        resp = oa_client.images.generate(
            model=model_name,
            prompt=prompt,
            size="1024x1024",
            n=1,
            response_format="b64_json",
        )

        b64 = getattr(resp.data[0], "b64_json", None)
        if b64:
            raw = base64.b64decode(b64)
            fname = f"city_{_safe_name(city_hint)}.png"
            fpath = os.path.join(IMG_DIR, fname)
            with open(fpath, "wb") as f:
                f.write(raw)
            print(f"[image] generated (b64) with {model_name}: {fpath}")
            return fpath

        url = getattr(resp.data[0], "url", None)
        if url:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            fname = f"city_{_safe_name(city_hint)}.png"
            fpath = os.path.join(IMG_DIR, fname)
            with open(fpath, "wb") as f:
                f.write(r.content)
            print(f"[image] generated (url) with {model_name}: {fpath}")
            return fpath

        print(f"[image] no b64/url in response: {resp}")
        return None

    except Exception as e:
        print(f"[image] {model_name} failed: {e}")
        traceback.print_exc()
        return None

def transcribe_audio_to_text(audio_path: str) -> str:
    """Mic → transcript (no translate, no auto-send)."""
    if not (oa_client and settings.OPENAI_API_KEY):
        return ""
    try:
        with open(audio_path, "rb") as f:
            tr = oa_client.audio.transcriptions.create(model="whisper-1", file=f)
        return tr.text or ""
    except Exception as e:
        print(f"[voice] transcription failed: {e}")
        traceback.print_exc()
        return ""

def tts_from_text(text: str) -> str | None:
    """User's typed message → TTS mp3 (on demand)."""
    if not (oa_client and settings.OPENAI_API_KEY) or not text.strip():
        return None
    model = getattr(settings, "TTS_MODEL", "gpt-4o-mini-tts")
    voice = getattr(settings, "TTS_VOICE", "alloy")
    out_path = os.path.join(AUDIO_DIR, "my_message.mp3")
    try:
        with oa_client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
        ) as response:
            response.stream_to_file(out_path)
        return out_path
    except Exception as e:
        print(f"[voice] tts failed: {e}")
        traceback.print_exc()
        return None

# ---------- Core Chat ----------
def chat_core(message, history, do_translate, lang_code):
    # agents.handle -> (reply, translated, flights, dest_label)
    reply, translated, flights, dest_label = orch.handle(
        message, want_translation=do_translate, target_lang=lang_code
    )
    df = pd.DataFrame(flights) if flights else None
    image_path = None
    if flights and dest_label:
        image_path = generate_city_image_1024(dest_label)

    return reply, df, (translated or ""), image_path

# ---------- UI ----------
with gr.Blocks(title="FlightChat Agents – Text + STT + Optional TTS") as demo:
    gr.Markdown(
        "# ✈️ FlightChat Agents\n"
        "- **Text chat** (auto city image on flight search)\n"
        "- **Voice → Text**: record and fill the message box (no auto-translate, no auto-send)\n"
        "- **Optional TTS**: read **your typed message** aloud when you click the button\n"
    )

    with gr.Row():
        do_translate = gr.Checkbox(label="Translate answer", value=False)
        lang = gr.Dropdown(choices=[c for c in LANG_CHOICES], value="en", label="Target language")

    flights_df = gr.Dataframe(label="Flight Results", interactive=False)
    translated_out = gr.Textbox(label="Translated Answer (Claude)")
    city_image = gr.Image(label="Destination City (1024×1024)", type="filepath")

    # Main chat
    chat = gr.ChatInterface(
        fn=chat_core,
        chatbot=gr.Chatbot(type="messages"),
        additional_inputs=[do_translate, lang],
        additional_outputs=[flights_df, translated_out, city_image],
        title="Flight Assistant",
        multimodal=False,
        examples=[
            ["Find me a cheap flight from Istanbul to London next Friday", False, "en"],
            ["I want to fly to Paris on 15 September", False, "en"],
            ["Check options to Berlin in the first week of October", False, "en"],
        ],
    )

    # --- Voice -> Text utility (fills the chat textbox only) ---
    gr.Markdown("### 🎤 Voice → Text (fills the message box)")
    with gr.Row():
        mic_audio = gr.Audio(sources=["microphone"], type="filepath", label="Record your voice")
        transcript_box = gr.Textbox(label="Transcript (preview)", interactive=False)
    with gr.Row():
        def do_transcribe(audio_file):
            txt = transcribe_audio_to_text(audio_file) if audio_file else ""
            # 1) transcript preview, 2) set chat textbox value
            return gr.update(value=txt), gr.update(value=txt)

        gr.Button("Transcribe to message box").click(
            do_transcribe, [mic_audio], [transcript_box, chat.textbox]
        )

    # --- Optional TTS for user's typed message ---
    gr.Markdown("### 🔊 Read my message (optional)")
    tts_audio_out = gr.Audio(label="Playback", type="filepath")

    def read_my_message(msg_text):
        path = tts_from_text(msg_text or "")
        return gr.update(value=path)

    gr.Button("Read my message").click(read_my_message, [chat.textbox], [tts_audio_out])

if __name__ == "__main__":
    demo.launch(share=settings.GRADIO_SHARE)
