import os
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voice Agent")


# ── TwiML entry point ──────────────────────────────────────────────
# Twilio hits this URL when a call comes in.
# It tells Twilio to open a Media Stream back to our websocket.
@app.post("/incoming-call")
async def incoming_call(request: Request):
    host = request.headers.get("host")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna" rate="85%">
    Please hold while we connect you.
  </Say>
  <Connect>
    <Stream url="wss://{host}/media-stream" />
  </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


# ── Websocket endpoint ─────────────────────────────────────────────
# Twilio streams real-time audio here.
@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("✅ Twilio connected to /media-stream")

    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            event = data.get("event")

            if event == "start":
                stream_sid = data["start"]["streamSid"]
                call_sid   = data["start"]["callSid"]
                logger.info(f"📞 Call started | callSid={call_sid} | streamSid={stream_sid}")

            elif event == "media":
                # Audio chunk arrives here (mulaw, 8kHz, base64 encoded)
                # Phase 4 will plug Silero VAD + STT here
                payload = data["media"]["payload"]
                logger.info(f"🎙️  Audio chunk received | size={len(payload)} bytes")

            elif event == "stop":
                logger.info("📴 Call ended by Twilio")
                break

    except WebSocketDisconnect:
        logger.info("🔌 Websocket disconnected")


# ── Health check ───────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "voice-agent"}