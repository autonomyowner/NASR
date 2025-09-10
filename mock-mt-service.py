#!/usr/bin/env python3
"""
Mock MT service for development and testing
Simulates the translation API without heavy ML dependencies
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
import time

app = FastAPI(title="Mock MT Service", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"service": "Mock MT Service", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

# Simple mock translations
MOCK_TRANSLATIONS = {
    "hello": {"fr": "bonjour", "es": "hola", "de": "hallo", "ar": "مرحبا"},
    "goodbye": {"fr": "au revoir", "es": "adiós", "de": "auf wiedersehen", "ar": "مع السلامة"},
    "thank you": {"fr": "merci", "es": "gracias", "de": "danke", "ar": "شكرا"},
    "how are you": {"fr": "comment allez-vous", "es": "¿cómo estás?", "de": "wie geht es dir", "ar": "كيف حالك"},
}

@app.websocket("/ws/translate")
async def websocket_translate(websocket: WebSocket):
    await websocket.accept()
    print("MT service WebSocket connection accepted")
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            print(f"Received: {message}")
            
            # Extract translation request
            text = message.get("text", "").lower()
            target_lang = message.get("target_language", "fr")
            chunk_id = message.get("chunk_id", 0)
            
            # Mock translation with slight delay to simulate processing
            await asyncio.sleep(0.05)  # 50ms delay
            
            # Find translation or return original text
            translated = text
            for phrase, translations in MOCK_TRANSLATIONS.items():
                if phrase in text:
                    translated = text.replace(phrase, translations.get(target_lang, phrase))
            
            # Send response
            response = {
                "type": "translation_chunk",
                "chunk_id": chunk_id,
                "original_text": message.get("text", ""),
                "translated_text": translated,
                "target_language": target_lang,
                "confidence": 0.95,
                "processing_time_ms": 50,
                "timestamp": time.time()
            }
            
            await websocket.send_text(json.dumps(response))
            print(f"Sent translation: {translated}")
            
    except WebSocketDisconnect:
        print("MT service WebSocket disconnected")
    except Exception as e:
        print(f"MT service error: {e}")

if __name__ == "__main__":
    print("Starting Mock MT Service on port 8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)