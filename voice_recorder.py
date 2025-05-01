import sounddevice as sd
import numpy as np
import wave
import boto3
import os
from datetime import datetime
from scipy.io.wavfile import write
import tempfile
import threading
import queue
import json
import time
import base64
import requests
from app.core.config import get_settings

class VoiceRecorder:
    def __init__(self):
        self.settings = get_settings()
        self.sample_rate = 44100  # Sample rate in Hz
        self.channels = 1  # Mono audio
        self.recording = False
        self.stream = None
        self.frames = []
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3',
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=self.settings.aws_region
        )
        
        self.bucket_name = self.settings.s3_bucket
        self.recordings_prefix = self.settings.s3_recordings_prefix
        self.transcripts_prefix = self.settings.s3_transcripts_prefix
        self.transcribe = boto3.client('transcribe')
        self.audio_queue = queue.Queue()

    def record_audio(self):
        """Record audio until stop is called"""
        self.recording = True
        frames = []
        
        def callback(indata, frames, time, status):
            if status:
                print(f"Error in callback: {status}")
            if self.recording:
                self.audio_queue.put(indata.copy())
            
        with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, callback=callback):
            while self.recording:
                if not self.audio_queue.empty():
                    frames.append(self.audio_queue.get())
        
        if frames:
            return np.concatenate(frames)
        return None

    def stop_recording(self):
        """Stop the recording"""
        self.recording = False

    def save_audio(self, recording, filename):
        """Save recording to WAV file"""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            write(temp_file.name, self.sample_rate, recording)
            return temp_file.name

    def upload_to_s3(self, file_path, object_name=None):
        """Upload file to S3 bucket"""
        if object_name is None:
            object_name = f"{self.recordings_prefix}{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, object_name)
            return f"s3://{self.bucket_name}/{object_name}"
        except Exception as e:
            print(f"Error uploading to S3: {e}")
            return None

    def transcribe_audio(self, s3_uri):
        """Transcribe audio using Amazon Transcribe"""
        try:
            job_name = f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.transcribe.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': s3_uri},
                MediaFormat='wav',
                LanguageCode='en-US'
            )
            
            # Wait for the job to complete
            while True:
                status = self.transcribe.get_transcription_job(TranscriptionJobName=job_name)
                if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                    break
                time.sleep(2)
            
            if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
                # Get the transcript
                transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
                response = requests.get(transcript_uri)
                transcript_data = response.json()
                return transcript_data['results']['transcripts'][0]['transcript']
            else:
                print(f"Transcription failed: {status['TranscriptionJob'].get('FailureReason', 'Unknown error')}")
                return None
            
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

    def save_transcript_to_s3(self, transcript, object_name=None):
        """Save transcript to S3"""
        if object_name is None:
            object_name = f"{self.transcripts_prefix}{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=transcript.encode('utf-8')
            )
            return f"s3://{self.bucket_name}/{object_name}"
        except Exception as e:
            print(f"Error saving transcript: {e}")
            return None

def main():
    recorder = VoiceRecorder()
    
    # Record audio
    recording = recorder.record_audio()
    
    # Save audio to temporary file
    audio_file = recorder.save_audio(recording, "recording.wav")
    
    # Upload to S3
    s3_uri = recorder.upload_to_s3(audio_file)
    if s3_uri:
        print(f"Audio uploaded to {s3_uri}")
        
        # Transcribe audio
        transcript = recorder.transcribe_audio(s3_uri)
        if transcript:
            print(f"Transcript: {transcript}")
            
            # Save transcript to S3
            transcript_uri = recorder.save_transcript_to_s3(transcript)
            if transcript_uri:
                print(f"Transcript saved to {transcript_uri}")

if __name__ == "__main__":
    main() 