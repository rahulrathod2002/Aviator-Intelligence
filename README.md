# Aviator Intelligence

Real-time Aviator analytics platform with a Python backend and a React frontend.

## Folder Structure

```text
.
├── backend
│   ├── analytics
│   ├── ocr
│   ├── services
│   ├── sources
│   ├── storage
│   ├── app.py
│   ├── config.py
│   ├── main.py
│   ├── models.py
│   └── requirements.txt
├── data
│   └── rounds.csv
└── frontend
    ├── src
    ├── index.html
    ├── package.json
    ├── tailwind.config.js
    └── vite.config.ts
```

## What Changed

- All Python runtime logic now lives under `backend/`.
- `backend/main.py` is the single backend entry point.
- Browser storage has been removed completely.
- Historical round storage now lives in `data/rounds.csv`.
- The frontend consumes backend WebSocket data only.
- Input failover now follows this priority:
  1. ADB device
  2. Browser capture
  3. `No Signal`

## Requirements

- Python 3.11+
- Node.js 20+
- `adb` available in `PATH` for primary capture
- Optional: Tesseract in `PATH` for OCR fallback
- Optional: Chrome or Playwright Chromium for browser fallback capture

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The backend starts a WebSocket server on `ws://localhost:8765`.

Notes:

- On startup, the backend creates `data/rounds.csv` if it does not exist.
- Startup retention loads the file, sorts by timestamp descending, keeps only the latest 3000 rows, and permanently removes older rows.
- New crashed rounds are appended to the CSV without rewriting the whole file.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend starts on `http://localhost:5173`.

## Runtime Model

### Round State Engine

- `WAITING`: countdown phase, no multiplier locked
- `FLYING`: live multiplier rising, white text
- `CRASHED`: final multiplier locked, red text

The backend maintains and broadcasts:

- `current_round`
- `previous_round`
- `next_round`
- `state`
- `multiplier`
- `confidence`
- `source`
- `status`

### Multi-Source Input

- `ADB` is the primary source.
- `Browser` capture is the automatic fallback.
- If both fail, the backend emits:

```json
{ "status": "NO_SIGNAL" }
```

### Storage Schema

`data/rounds.csv` uses:

```text
timestamp,round_id,multiplier,state,source
```

## Probability Analytics

The backend computes probability guidance from historical crashed rounds using:

- rolling median
- volatility index
- low streak detection
- high streak detection
- distribution buckets

The output is labeled as probability only, not a deterministic prediction.

## Verification Completed

- Python modules compiled with `python -m compileall backend`
- Frontend production build completed with `npm run build`

## Design Decisions

- CSV is the primary storage format because it is append-friendly and easy to inspect operationally.
- Retention is enforced at backend startup to keep runtime memory and frontend payloads bounded.
- OCR uses ROI cropping, color masking, thresholding, and multiple OCR passes before selecting the highest-confidence result.
- Source selection is centralized in the backend so the frontend always receives a single normalized live stream.
- Probability analytics are computed server-side so the browser remains stateless and disposable.
