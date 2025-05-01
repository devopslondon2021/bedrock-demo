from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from pydantic import validator

class Settings(BaseSettings):
    # AWS Settings
    aws_region: str = "us-east-1"
    aws_access_key_id: str
    aws_secret_access_key: str
    
    # S3 Settings
    s3_bucket: str = "demo-bucket-986123"
    s3_recordings_prefix: str = "recordings/"
    s3_transcripts_prefix: str = "transcripts/"
    s3_excel_file: str = "source/GoogleSheet/CarSale.xlsx"
    
    # LLM Settings
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    # Application Settings
    debug: bool = False
    
    @validator('debug', pre=True)
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings() 