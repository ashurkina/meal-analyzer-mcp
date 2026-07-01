from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["low", "medium", "high"]


class FoodItem(BaseModel):
    name: str = Field(description="Name of the identified food or drink item")
    estimated_grams: float = Field(description="Estimated portion weight in grams")
    calories: float = Field(description="Estimated calories (kcal) for this portion")
    protein_g: float = Field(description="Estimated protein in grams")
    carbs_g: float = Field(description="Estimated carbohydrates in grams")
    fat_g: float = Field(description="Estimated fat in grams")
    confidence: Confidence = Field(description="Confidence in this item's identification and estimate")


class Totals(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class MealAnalysis(BaseModel):
    items: list[FoodItem]
    totals: Totals
    overall_confidence: Confidence = Field(
        description="Overall confidence in the analysis as a whole"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Caveats about this estimate, e.g. 'Portion size estimated visually', "
            "'Cooking oil may not be visible'"
        ),
    )
