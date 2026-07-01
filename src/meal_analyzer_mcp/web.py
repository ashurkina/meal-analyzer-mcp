from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from .gemini_client import GeminiAnalysisError
from .gemini_client import analyze_meal_image as run_gemini_analysis

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Meal Analyzer</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }
  h1 { margin-bottom: 0.25rem; }
  p.description { color: #555; margin-top: 0; }
  .upload-row { display: flex; gap: 0.75rem; align-items: center; margin: 1.5rem 0; flex-wrap: wrap; }
  #context-input { flex: 1; min-width: 200px; padding: 0.4rem 0.5rem; }
  button { padding: 0.5rem 1rem; cursor: pointer; }
  button:disabled { cursor: default; opacity: 0.6; }
  #preview { display: none; max-width: 320px; max-height: 320px; margin-top: 0.5rem; border-radius: 8px; object-fit: cover; }
  #result { margin-top: 1.5rem; }
  #error { color: #b00020; margin-top: 1rem; }
  table { border-collapse: collapse; width: 100%; margin-top: 0.5rem; }
  th, td { text-align: left; padding: 0.35rem 0.5rem; border-bottom: 1px solid #ddd; font-size: 0.9rem; }
  .totals { font-weight: 600; }
  .warnings { margin-top: 1rem; font-size: 0.85rem; color: #663c00; background: #fff8e1; padding: 0.75rem 1rem; border-radius: 6px; }
  .confidence { font-size: 0.85rem; color: #555; }
</style>
</head>
<body>
  <h1>Meal Analyzer</h1>
  <p class="description">
    Upload a meal photo to get an estimated breakdown of foods, portion sizes,
    calories, and macronutrients. Estimates only — a single photo can't reveal
    hidden ingredients, cooking oil, or exact weights.
  </p>

  <div class="upload-row">
    <input type="file" id="image-input" accept="image/*">
    <input type="text" id="context-input" placeholder="Optional context (e.g. recipe, ingredients, portion size)">
    <button id="analyze-btn">Analyze</button>
  </div>

  <img id="preview" alt="Selected meal photo preview">

  <div id="error"></div>
  <div id="result"></div>

<script>
const input = document.getElementById('image-input');
const contextInput = document.getElementById('context-input');
const button = document.getElementById('analyze-btn');
const resultEl = document.getElementById('result');
const errorEl = document.getElementById('error');
const previewEl = document.getElementById('preview');

input.addEventListener('change', () => {
  const file = input.files[0];
  if (!file) {
    previewEl.style.display = 'none';
    previewEl.src = '';
    return;
  }
  previewEl.src = URL.createObjectURL(file);
  previewEl.style.display = 'block';
});

button.addEventListener('click', async () => {
  const file = input.files[0];
  errorEl.textContent = '';
  resultEl.innerHTML = '';

  if (!file) {
    errorEl.textContent = 'Please choose an image first.';
    return;
  }

  const formData = new FormData();
  formData.append('image', file);
  if (contextInput.value.trim()) {
    formData.append('context', contextInput.value.trim());
  }

  button.disabled = true;
  button.textContent = 'Analyzing…';

  try {
    const response = await fetch('/analyze', { method: 'POST', body: formData });
    const data = await response.json();

    if (!response.ok) {
      errorEl.textContent = data.error || 'Analysis failed.';
      return;
    }

    renderResult(data);
  } catch (err) {
    errorEl.textContent = 'Request failed: ' + err;
  } finally {
    button.disabled = false;
    button.textContent = 'Analyze';
  }
});

function renderResult(data) {
  const rows = data.items.map(item => `
    <tr>
      <td>${item.name}</td>
      <td>${item.estimated_grams} g</td>
      <td>${item.calories} kcal</td>
      <td>${item.protein_g} g</td>
      <td>${item.carbs_g} g</td>
      <td>${item.fat_g} g</td>
      <td>${item.confidence}</td>
    </tr>
  `).join('');

  const warnings = (data.warnings || []).map(w => `<li>${w}</li>`).join('');

  resultEl.innerHTML = `
    <table>
      <thead>
        <tr><th>Item</th><th>Grams</th><th>Calories</th><th>Protein</th><th>Carbs</th><th>Fat</th><th>Confidence</th></tr>
      </thead>
      <tbody>
        ${rows}
        <tr class="totals">
          <td>Total</td>
          <td></td>
          <td>${data.totals.calories} kcal</td>
          <td>${data.totals.protein_g} g</td>
          <td>${data.totals.carbs_g} g</td>
          <td>${data.totals.fat_g} g</td>
          <td></td>
        </tr>
      </tbody>
    </table>
    <p class="confidence">Overall confidence: ${data.overall_confidence}</p>
    ${warnings ? `<div class="warnings"><strong>Warnings</strong><ul>${warnings}</ul></div>` : ''}
  `;
}
</script>
</body>
</html>
"""


async def handle_index(request: Request) -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


async def handle_analyze(request: Request) -> JSONResponse:
    form = await request.form()
    upload = form.get("image")

    if upload is None or not hasattr(upload, "read"):
        return JSONResponse({"error": "No image file provided"}, status_code=400)

    image_bytes = await upload.read()
    if not image_bytes:
        return JSONResponse({"error": "Uploaded image is empty"}, status_code=400)

    mime_type = upload.content_type or "application/octet-stream"
    context = form.get("context") or None

    try:
        result = run_gemini_analysis(image_bytes, mime_type, context)
    except GeminiAnalysisError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)

    return JSONResponse(result.model_dump())
