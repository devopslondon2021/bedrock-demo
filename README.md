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
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
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

# Bedrock Car Sales Integration

## Environment Setup

### Google Sheets Integration

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

4. Create Service Account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the service account details:
     - Name: e.g., "Bedrock Sheets Service"
     - ID: will be auto-generated
     - Description: optional
   - Click "Create and Continue"
   - For "Grant this service account access to project", select:
     - Role: "Editor" (for full access to sheets)
   - Click "Done"

5. Create and download service account key:
   - Click on the newly created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format
   - Click "Create"
   - The key file will be downloaded automatically
   - Save it as `service-account.json` in your project directory

6. Create a Google Sheet:
   - Go to [Google Sheets](https://sheets.google.com)
   - Create a new spreadsheet
   - Copy the spreadsheet ID from the URL:
     - URL format: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
   - Share the spreadsheet with the service account email (found in your service-account.json)

7. Update your `.env` file:
```bash
# Google Sheets Settings
GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id
```

### Required Environment Variables
Copy `.env.example` to `.env` and fill in your values:

```bash
# AWS Settings
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key

# S3 Settings
S3_BUCKET=your_bucket_name
S3_RECORDINGS_PREFIX=recordings/
S3_TRANSCRIPTS_PREFIX=transcripts/

# Google Sheets Settings
GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id

# LLM Settings
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Application Settings
DEBUG=False
```

### Security Notes
- Never commit your `.env` file or service account key to version control
- Keep your credentials secure and rotate them regularly
- Use appropriate IAM roles and permissions for AWS services
- Store the service account key file securely and reference it in your `.env` file