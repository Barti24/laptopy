from typing import Optional
from pydantic import BaseModel, Field

class Listing(BaseModel):
    id: str
    title: str
    price: float
    currency: str = "PLN"
    description: str
    url: str
    platform: str  # "OLX" or "Vinted"
    image_url: Optional[str] = None

class EvaluationResult(BaseModel):
    estimated_market_value: float = Field(..., description="Estimated resale market value in PLN")
    estimated_profit: float = Field(..., description="Estimated profit in PLN after flipping (market value minus listing price)")
    reasoning: str = Field(..., description="Detailed explanation for the valuation and profit estimation")
    is_profitable: bool = Field(False, description="Whether estimated profit exceeds threshold")
