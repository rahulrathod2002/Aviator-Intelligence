# Aviator Real-Time Analytics Platform

High-accuracy crash-game monitoring built for local, low-latency workflows. The system captures live frames from an Android device over ADB, extracts multiplier values with OCR, streams them via WebSocket, and renders real-time analytics in a React dashboard. All logic and storage live in the browser (IndexedDB + localStorage). No backend or database required.

## Architecture

- `capture`: Python ADB + OCR pipeline with reconnect logic, ROI preprocessing, retry handling, and WebSocket broadcast.
- `frontend`: React + Tailwind dashboard with live charts, analytics panels, AI insight, and local storage.

## Prerequisites

- Node.js 20+
- Python 3.11+
- Android Debug Bridge (`adb`) in PATH
- Optional: Tesseract installed locally for OCR fallback
- Optional: Groq API key for AI insights

## Install and Run (Clear Commands)

From the project root:

```bash
npm install
npm run dev
```

On first run, `npm run dev` will:

- install frontend dependencies (if missing)
- create `capture/.venv` and install Python requirements
- start the React frontend and Python capture service

Open the UI at:

```bash
http://localhost:5173
```

WebSocket stream runs on:

```bash
ws://localhost:8765
```

### Manual (Optional)

If you want to run each service directly:

```bash
cd frontend
npm install
npm run dev
```

```bash
cd capture
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Data Flow

1. Python capture polls the device via ADB.
2. Frames are cropped + preprocessed for OCR.
3. OCR runs multi-pass recognition and confidence selection.
4. Multipliers are smoothed and streamed via WebSocket.
5. Frontend consumes the stream, computes analytics, stores history in IndexedDB, and renders the UI.

## Accuracy Tuning

OCR reliability depends on ROI alignment and consistent UI scale. Adjust ROI settings in:

`capture/src/utils/config.py`

Use these tools to debug ROI and OCR:

```bash
python tools/grab_frame.py
python tools/inspect_ocr.py
```

Enable debug overlay in `config.py`:

```python
debug_roi = True
```

## AI Insights (Optional)

Paste your Groq API key into the UI input field. It is stored in localStorage under the key `groq_api_key`. AI insights are probabilistic only and are never presented as deterministic predictions.

## Performance Notes

- Poll interval is configurable (`poll_interval_ms`) in `config.py`.
- Frontend history is capped at 300 points in memory.
- Outliers are flagged and smoothed locally to reduce noise.

## Deliverables Included

- full codebase
- local run instructions
- OCR + analytics pipeline
- production-oriented single-page UI
