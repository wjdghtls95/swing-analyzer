# analyze/schema.py
from pydantic import BaseModel

class AnalyzeResponse(BaseModel):
    swingId: str
    elbowAvgAngle: float
    feedback: str
    landmarkCount: int

class UrlRequest(BaseModel):
    s3_url: str
