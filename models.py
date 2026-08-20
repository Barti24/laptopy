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
    detected_fault: str = Field(..., description="Krótki opis wykrytej usterki na podstawie opisu ogłoszenia")
    difficulty_level: str = Field("Średnia", description="Poziom trudności naprawy: Prosta / Średnia / Trudna")
    estimated_parts_cost_pln: int = Field(0, description="Szacowany koszt części w PLN")
    estimated_market_value_working_pln: int = Field(0, description="Realna wartość rynkowa po naprawie na OLX/Allegro w PLN")
    net_profit_pln: int = Field(0, description="Zysk netto: Market Value - (Cena Zakupu + Wysyłka 15 zł + Parts Cost)")
    roi_percentage: int = Field(0, description="ROI w procentach: Zysk netto / całkowite wydatki * 100")
    is_profitable: bool = Field(False, description="true jeśli net_profit >= 100 PLN i brak ryzyka uszkodzenia płyty głównej/CPU")
    recommendation_reason: str = Field(..., description="Jedno zdanie wyjaśniające dlaczego warto lub nie warto brać")
