# Voice Recording and Transcription Demo

This demo records your voice, processes it using Amazon Nova Sonic on AWS Bedrock, and stores both the audio and transcription in S3.

## Prerequisites

1. AWS Account with access to:
   - Amazon Bedrock (Nova Sonic model enabled)
   - Amazon S3
   - Appropriate IAM permissions

2. Python 3.8 or higher
3. Working microphone

## Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd voice-transcription-demo
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create an S3 bucket in your AWS account

5. Copy `.env.example` to `.env` and fill in your AWS credentials and S3 bucket name:
```bash
cp .env.example .env
```

6. Edit `.env` with your details:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
```

## Usage

1. Run the script:
```bash
python voice_recorder.py
```

2. The script will:
   - Record audio for 10 seconds (configurable in the code)
   - Upload the audio to S3
   - Transcribe the audio using Nova Sonic
   - Save the transcription to S3
   - Print the transcript and S3 URIs

## Troubleshooting

1. **Audio Recording Issues**
   - Ensure your microphone is properly connected and set as default input device
   - Check system permissions for microphone access

2. **AWS Errors**
   - Verify AWS credentials are correct
   - Ensure S3 bucket exists and is accessible
   - Check that Nova Sonic model is enabled in your AWS account

3. **Python Dependencies**
   - On Windows, you might need to install PyAudio using a wheel file
   - On Linux, you might need to install portaudio19-dev: `sudo apt-get install portaudio19-dev`

## Notes

- The demo records in mono audio at 44.1kHz
- Audio files and transcripts are stored with timestamps in their filenames
- Temporary audio files are automatically cleaned up
- Default recording duration is 10 seconds (can be modified in main()) 