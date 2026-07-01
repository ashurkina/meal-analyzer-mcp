import base64
import os
from typing import Annotated

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .gemini_client import GeminiAnalysisError
from .gemini_client import analyze_meal_image as run_gemini_analysis
from .schema import MealAnalysis
from .web import handle_analyze, handle_index

load_dotenv()

TOOL_DESCRIPTION = (
    "Analyze a meal photo and estimate detected foods, portion sizes, calories, "
    "and macronutrients. Returns structured JSON. Estimates are based only on "
    "what's visible in the image — hidden ingredients, cooking oils, sauces, "
    "and exact weights cannot be determined from a single photo."
)

_transport = os.environ.get("MCP_TRANSPORT", "stdio")
if _transport == "streamable-http":
    mcp = FastMCP(
        "meal-analyzer",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
    )
else:
    mcp = FastMCP("meal-analyzer")

mcp.custom_route("/", methods=["GET"])(handle_index)
mcp.custom_route("/analyze", methods=["POST"])(handle_analyze)


@mcp.tool(description=TOOL_DESCRIPTION)
def analyze_meal_image(
    image_base64: str,
    mime_type: str,
    context: Annotated[
        str | None,
        Field(
            description=(
                "Optional short context about the meal to help the model "
                "(e.g. recipe, ingredients used, known portion size)"
            )
        ),
    ] = None,
) -> MealAnalysis:
    if not image_base64:
        raise ValueError("image_base64 is required")
    if not mime_type:
        raise ValueError("mime_type is required")

    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError(f"image_base64 is not valid base64 data: {exc}") from exc

    if not image_bytes:
        raise ValueError("Decoded image data is empty")

    try:
        return run_gemini_analysis(image_bytes, mime_type, context)
    except GeminiAnalysisError as exc:
        raise ValueError(str(exc)) from exc


def main() -> None:
    mcp.run(transport=_transport)


if __name__ == "__main__":
    main()
