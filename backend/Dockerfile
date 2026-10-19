FROM debian:bookworm-slim AS wireless-build
RUN apt-get update && apt-get install -y --no-install-recommends g++ cmake make && rm -rf /var/lib/apt/lists/*
COPY wireless-lab/cpp /src
RUN cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Release && cmake --build /build -j2 && ctest --test-dir /build --output-on-failure
FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tshark && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home appuser
COPY backend/app ./app
COPY evidence ./evidence
COPY wireless-lab/python ./wireless-lab/python
COPY wireless-lab/fixtures ./wireless-lab/fixtures
COPY wireless-lab/scenarios ./wireless-lab/scenarios
COPY --from=wireless-build /build/wireless_analyzer /usr/local/bin/wireless-analyzer
ENV WIRELESS_LAB_ROOT=/app/wireless-lab WIRELESS_ANALYZER=/usr/local/bin/wireless-analyzer
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
