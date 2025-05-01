from pydantic import BaseModel, Field
from typing import List, Optional

class Customer(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str

class Vehicle(BaseModel):
    make: str
    model: str

class ConfidenceScores(BaseModel):
    name: int = Field(ge=0, le=100)
    vehicle: int = Field(ge=0, le=100)
    dob: int = Field(ge=0, le=100)
    post_code: int = Field(ge=0, le=100)

class TranscriptAnalysis(BaseModel):
    customer: Customer
    vehicle: Vehicle
    date_of_birth: str
    post_code: str
    confidence_scores: ConfidenceScores
    missing_fields: List[str]
    ambiguities: List[str] 