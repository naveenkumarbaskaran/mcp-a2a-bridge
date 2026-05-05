FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir "."

FROM python:3.12-slim

LABEL maintainer="Naveen Kumar Baskaran <naveenkb142@gmail.com>"
LABEL org.opencontainers.image.source="https://github.com/naveenkumarbaskaran/mcp-a2a-bridge"
LABEL org.opencontainers.image.description="Bidirectional bridge between MCP and A2A protocols"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/mcp-a2a-bridge /usr/local/bin/mcp-a2a-bridge

EXPOSE 8000

ENTRYPOINT ["mcp-a2a-bridge"]
CMD ["--help"]
