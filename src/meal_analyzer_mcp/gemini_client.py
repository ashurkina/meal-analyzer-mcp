import os

from google import genai
from google.genai import types

from .schema import MealAnalysis

DEFAULT_MODEL = "gemini-2.5-flash"

PROMPT = """You are a nutrition estimation assistant. Look at the meal photo and:

1. Identify each distinct food or drink item visible in the image.
2. For each item, estimate the portion weight in grams, and estimate calories,
   protein, carbs, and fat for that portion.
3. Sum the per-item values into overall totals.
4. Set an overall_confidence for the analysis as a whole.
5. Populate warnings with specific caveats about this estimate.

Important limitation: your estimate is based only on what is visible in a single
photo. Hidden ingredients, cooking oil, sauces, dressings, and exact portion
weights cannot be determined from an image alone. Reflect this uncertainty in
overall_confidence and call out relevant caveats in warnings (e.g. "Portion size
estimated visually", "Cooking oil may not be visible", "Sauce/dressing quantity
unknown").

The user may also provide short additional context about the meal (e.g. recipe
details, ingredients used, portion size). If given, use it to refine your
estimate and give it more weight than a visual guess.
"""


class GeminiAnalysisError(Exception):
    pass


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise GeminiAnalysisError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set"
        )
    return genai.Client(api_key=api_key)


def analyze_meal_image(
    image_bytes: bytes, mime_type: str, context: str | None = None
) -> MealAnalysis:
    client = _get_client()
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    prompt = PROMPT
    if context:
        prompt += f'\n\nUser-provided context about this meal: "{context}"'

    try:
        response = client.models.generate_content(
            model=model,
            contents=[prompt, image_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MealAnalysis,
            ),
        )
    except Exception as exc:
        raise GeminiAnalysisError(f"Gemini request failed: {exc}") from exc

    parsed = response.parsed
    if parsed is None:
        raise GeminiAnalysisError("Gemini did not return a parseable structured response")
    return parsed
