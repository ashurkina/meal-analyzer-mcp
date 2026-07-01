FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

RUN useradd --create-home appuser
USER appuser

ENV MCP_TRANSPORT=streamable-http
EXPOSE 8000

CMD ["meal-analyzer-mcp"]
