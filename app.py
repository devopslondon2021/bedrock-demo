from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
from voice_recorder import VoiceRecorder
import base64
import os
from dotenv import load_dotenv
import asyncio
import threading

load_dotenv()

app = FastAPI()
recorder = VoiceRecorder()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get():
    with open("static/index.html") as f:
        return f.read()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    recording_thread = None
    
    try:
        while True:
            data = await websocket.receive_text()
            command = json.loads(data)
            
            if command["action"] == "start_recording":
                # Start recording in a separate thread
                def record():
                    recording = recorder.record_audio()
                    if recording is not None:
                        # Save and upload
                        audio_file = recorder.save_audio(recording, "recording.wav")
                        asyncio.run(websocket.send_json({
                            "status": "recording_stopped"
                        }))
                        
                        s3_uri = recorder.upload_to_s3(audio_file)
                        if s3_uri:
                            # Transcribe
                            asyncio.run(websocket.send_json({
                                "status": "transcribing"
                            }))
                            
                            transcript = recorder.transcribe_audio(s3_uri)
                            if transcript:
                                # Save transcript
                                transcript_uri = recorder.save_transcript_to_s3(transcript)
                                
                                asyncio.run(websocket.send_json({
                                    "status": "success",
                                    "transcript": transcript,
                                    "audio_uri": s3_uri,
                                    "transcript_uri": transcript_uri
                                }))
                            else:
                                asyncio.run(websocket.send_json({
                                    "status": "error",
                                    "message": "Transcription failed"
                                }))
                        else:
                            asyncio.run(websocket.send_json({
                                "status": "error",
                                "message": "Failed to upload audio"
                            }))
                
                recording_thread = threading.Thread(target=record)
                recording_thread.start()
                await websocket.send_json({"status": "recording_started"})
                
            elif command["action"] == "stop_recording":
                if recording_thread and recording_thread.is_alive():
                    recorder.stop_recording()
                    recording_thread.join()
            
    except Exception as e:
        if recording_thread and recording_thread.is_alive():
            recorder.stop_recording()
            recording_thread.join()
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 