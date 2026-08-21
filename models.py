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
    category: str = "Inne"
    image_url: Optional[str] = None

class EvaluationResult(BaseModel):
    item_title: str = Field(..., description="Tytuł przedmiotu")
    category: str = Field(..., description="Kategoria sprzętu")
    detected_fault: str = Field("Brak opisu usterki", description="Krótki opis usterki lub stanu z ogłoszenia")
    difficulty_level: str = Field("Średnia", description="Poziom trudności naprawy: Prosta / Średnia / Trudna")
    deal_score: int = Field(1, description="Ocena opłacalności w skali od 1 do 10")
    verdict: str = Field("ODRZUĆ", description="Werdykt AI: 'OKAZJA' (score 8-10), 'OBSERWUJ' (score 5-7), 'ODRZUĆ' (score 1-4)")
    estimated_market_value: int = Field(0, description="Prognozowana rynkowa cena sprzedaży sprawnego sprzętu w PLN")
    estimated_repair_cost: int = Field(0, description="Szacowany koszt części / naprawy w PLN")
    net_profit_pln: int = Field(0, description="Zysk netto: market_value - (cena_zakupu + 30 PLN + repair_cost)")
    roi_percentage: int = Field(0, description="ROI w procentach: Zysk netto / całkowite wydatki * 100")
    is_profitable: bool = Field(False, description="True jeśli deal_score >= 5 (verdict 'OKAZJA' lub 'OBSERWUJ') i urządzenie kwalifikuje się do zakupu")
    reasoning: str = Field(..., description="Zwięzłe uzasadnienie decyzji (1-2 zdania)")

    @property
    def estimated_parts_cost_pln(self) -> int:
        """Alias for estimated_repair_cost for backward compatibility."""
        return self.estimated_repair_cost

    @property
    def estimated_resale_price_pln(self) -> int:
        """Alias for estimated_market_value for backward compatibility."""
        return self.estimated_market_value

    @property
    def recommendation_reason(self) -> str:
        """Alias for reasoning for backward compatibility."""
        return self.reasoning
