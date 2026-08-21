from typing import Optional, List, Union
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
    deal_type: str = Field("BRAK_ZYSKU", description="'OKAZJA_FLIP', 'OKAZJA_NAPRAWA', lub 'BRAK_ZYSKU'")
    deal_score: int = Field(1, description="Ocena opłacalności w skali od 1 do 10")

    # Financials
    estimated_market_value: int = Field(0, description="Prognozowana cena rynkowa sprawnego sprzętu w PLN")
    estimated_parts_cost: int = Field(0, description="Szacowany koszt części zamiennych w PLN (0 dla OKAZJA_FLIP)")
    estimated_net_profit: int = Field(0, description="Zysk na czysto w PLN po potrąceniu zakupu, części i 20 PLN wysyłki")
    roi_percentage: int = Field(0, description="ROI w procentach: Zysk netto / całkowite wydatki * 100")

    # Strategy & Risk
    negotiation_target: int = Field(0, description="Sugerowana kwota pierwszej oferty negocjacyjnej na Vinted w PLN")
    market_liquidity: str = Field("ŚREDNIO", description="'BARDZO SZYBKO', 'ŚREDNIO', lub 'NISKA PŁYNNOŚĆ'")
    risk_assessment: str = Field("ŚREDNIE", description="Poziom ryzyka ('NISKIE', 'ŚREDNIE', 'WYSOKIE') wraz z zwięzłym uzasadnieniem")
    salvage_value: int = Field(0, description="Przewidywana wartość samych sprawnych części w PLN (Plan B / dawca)")

    # Technical Analysis (mainly for OKAZJA_NAPRAWA)
    fault_analysis: str = Field("Brak usterki / Sprzęt sprawny", description="Zwięzła diagnoza techniczna")
    repair_difficulty: str = Field("Brak", description="'ŁATWA', 'ŚREDNIA', 'TRUDNA', lub 'Brak'")
    repair_steps: Union[List[str], str] = Field("Brak wymagań naprawczych", description="Konkretny plan naprawczy (2-3 punkty)")

    is_profitable: bool = Field(False, description="True jeśli OKAZJA_FLIP z net_profit >= 80 PLN lub OKAZJA_NAPRAWA z net_profit >= 100 PLN")
    reasoning: str = Field(..., description="Zwięzłe uzasadnienie decyzji (1-2 zdania)")

    @property
    def verdict(self) -> str:
        if self.deal_type == "OKAZJA_FLIP":
            return "OKAZJA FLIP"
        elif self.deal_type == "OKAZJA_NAPRAWA":
            return "OKAZJA NAPRAWA"
        return "ODRZUĆ"

    @property
    def estimated_parts_cost_pln(self) -> int:
        return self.estimated_parts_cost

    @property
    def estimated_resale_price_pln(self) -> int:
        return self.estimated_market_value

    @property
    def recommendation_reason(self) -> str:
        return self.reasoning
