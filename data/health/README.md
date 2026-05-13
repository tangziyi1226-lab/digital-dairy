# Health Imports

Put Xiaomi / Mi Fitness day-level health exports here as `.csv` or `.json`.

The generator supports these fields:

```csv
date,sleep_minutes,steps,active_minutes,workout_minutes,distance_km,calories
2026-05-12,420,8632,48,32,5.4,420
```

Or JSON:

```json
[
  {
    "date": "2026-05-12",
    "sleep_minutes": 420,
    "steps": 8632,
    "active_minutes": 48,
    "workout_minutes": 32,
    "distance_km": 5.4,
    "calories": 420
  }
]
```

Recommended privacy boundary: import day-level summaries only. You do not need to import GPS routes, heart-rate series, or raw minute-level data for the daily narrative.
