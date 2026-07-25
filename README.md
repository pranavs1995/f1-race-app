# Formula One Race Application

A small Flask-backed Formula One race simulator that keeps the race logic in one place and exposes it through a web UI, an API-driven demo, and a pytest suite.

## What’s included

- Race state and rules in car.py
- Winner selection in race_engine.py
- Flask API and web server in app.py
- API-driven demo script in demo.py
- Interactive dashboard in index.html
- Payout simulation for race winners in payout_service.py
- Unit tests in test_race_module.py

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run the demo

```bash
python3 demo.py
```

This starts the Flask backend, opens the UI, and drives the race flow through the same API routes used by the dashboard.

## Run the web app

```bash
python3 app.py
```

Then open http://127.0.0.1:5000 in your browser.

## Run the tests

```bash
python3 -m pytest -v
```

The current suite covers lap timing, pit stop behavior, tyre alerts, winner selection, speed validation, and payout handling.
