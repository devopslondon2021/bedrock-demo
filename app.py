from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
import uvicorn
import json
from voice_recorder import VoiceRecorder
from app.services.llm_analyzer import LLMAnalyzer
from app.services.excel_service import ExcelService
import base64
import os
from dotenv import load_dotenv
import asyncio
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()
recorder = VoiceRecorder()
llm_analyzer = LLMAnalyzer()
excel_service = ExcelService()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get():
    with open("static/index.html") as f:
        return f.read()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            data = await websocket.receive_json()
            logger.info(f"Received WebSocket action: {data['action']}")
            
            if data["action"] == "start_recording":
                await websocket.send_json({
                    "status": "recording_started"
                })
                logger.info("Started recording")
                
                def record():
                    try:
                        logger.info("Recording audio...")
                        recording = recorder.record_audio()
                        if recording is None:
                            logger.error("Failed to record audio")
                            asyncio.run(websocket.send_json({
                                "status": "error",
                                "message": "Failed to record audio. Please try again."
                            }))
                            return
                        
                        # Save to temporary file first
                        logger.info("Saving audio to temporary file...")
                        temp_file = recorder.save_audio(recording, "recording.wav")
                        
                        # Upload to S3
                        logger.info("Uploading to S3...")
                        s3_uri = recorder.upload_to_s3(temp_file)
                        
                        if s3_uri:
                            # Transcribe
                            logger.info("Starting transcription...")
                            asyncio.run(websocket.send_json({
                                "status": "transcribing"
                            }))
                            
                            transcript = recorder.transcribe_audio(s3_uri)
                            if transcript:
                                # Save transcript
                                logger.info("Saving transcript to S3...")
                                transcript_uri = recorder.save_transcript_to_s3(transcript)
                                
                                # Analyze with LLM
                                logger.info("Analyzing transcript with LLM...")
                                asyncio.run(websocket.send_json({
                                    "status": "analyzing"
                                }))
                                
                                analysis = llm_analyzer.analyze_transcript(transcript)
                                logger.info(f"Analysis results: {json.dumps(analysis, indent=2)}")
                                
                                # Submit to Excel in S3
                                logger.info("Submitting to Excel in S3...")
                                excel_submitted = excel_service.submit_response(analysis)
                                
                                asyncio.run(websocket.send_json({
                                    "status": "success",
                                    "transcript": transcript,
                                    "audio_uri": s3_uri,
                                    "transcript_uri": transcript_uri,
                                    "analysis": analysis,
                                    "excel_submitted": excel_submitted
                                }))
                                logger.info("Processing completed successfully")
                            else:
                                logger.error("Transcription failed")
                                asyncio.run(websocket.send_json({
                                    "status": "error",
                                    "message": "Failed to transcribe audio. Please try again."
                                }))
                        else:
                            logger.error("Failed to upload to S3")
                            asyncio.run(websocket.send_json({
                                "status": "error",
                                "message": "Failed to upload audio to S3. Please try again."
                            }))
                    except Exception as e:
                        logger.error(f"Error during processing: {str(e)}")
                        asyncio.run(websocket.send_json({
                            "status": "error",
                            "message": f"An error occurred: {str(e)}"
                        }))
                
                # Start recording in a separate thread
                threading.Thread(target=record).start()
                
            elif data["action"] == "stop_recording":
                logger.info("Stopping recording")
                recorder.stop_recording()
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        if websocket.client_state.CONNECTED:
            await websocket.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 