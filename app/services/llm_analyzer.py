import boto3
from typing import Dict, Any
import json
import os
from ..core.logger import logger

class LLMAnalyzer:
    def __init__(self):
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-east-1'
        )
        
    def _get_analysis_prompt(self, transcript: str) -> str:
        return f"""Human: You are an AI assistant helping to extract specific information from a customer call transcript for a car sale inquiry. Please analyze the following transcript and extract the required information in a structured format.

Transcript:
{transcript}

Please extract the following information:
1. Customer Name (First, Middle if provided, Last)
2. Car Details (Make and Model)
3. Date of Birth
4. Post Code

Requirements:
- Extract only the information that is explicitly mentioned in the transcript
- For missing information, mark as "Not provided"
- Format dates as YYYY-MM-DD
- Validate post code format if possible
- If multiple values are mentioned for the same field, note all mentions and choose the most recently confirmed one
- Include "middle_name" in missing_fields if it is not provided
- Include "last_name" in missing_fields if it is not provided

Business Logic Validation:
- Calculate customer's age from DOB and flag if under 18 years old
- Flag if customer's age seems unreasonably young (e.g., under 16) for a car purchase
- Validate post code format based on country standards (e.g., UK format)
- Check if car make and model combination is valid
- Flag any unusual patterns or potential concerns

Return the information in the following JSON format:
{{
    "customer": {{
        "first_name": "string",
        "middle_name": "string or null",
        "last_name": "string"
    }},
    "vehicle": {{
        "make": "string",
        "model": "string"
    }},
    "date_of_birth": "YYYY-MM-DD",
    "post_code": "string",
    "confidence_scores": {{
        "name": 0-100,
        "vehicle": 0-100,
        "dob": 0-100,
        "post_code": 0-100
    }},
    "missing_fields": ["field1", "field2"],
    "ambiguities": ["description of any unclear information or business logic concerns"]
}}"""

    def analyze_transcript(self, transcript: str) -> Dict[str, Any]:
        """Analyze the transcript using Amazon Bedrock"""
        try:
            prompt = self._get_analysis_prompt(transcript)
            
            response = self.bedrock_runtime.invoke_model(
                modelId='us.anthropic.claude-3-7-sonnet-20250219-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.1,
                    "top_p": 0.9
                })
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            # Extract JSON from the response
            json_str = content[content.find('{'):content.rfind('}')+1]
            analysis = json.loads(json_str)
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing transcript: {e}")
            return {
                "error": str(e),
                "customer": {
                    "first_name": "Not provided",
                    "middle_name": None,
                    "last_name": "Not provided"
                },
                "vehicle": {
                    "make": "Not provided",
                    "model": "Not provided"
                },
                "date_of_birth": "Not provided",
                "post_code": "Not provided",
                "confidence_scores": {
                    "name": 0,
                    "vehicle": 0,
                    "dob": 0,
                    "post_code": 0
                },
                "missing_fields": ["all"],
                "ambiguities": ["Failed to analyze transcript"]
            } 