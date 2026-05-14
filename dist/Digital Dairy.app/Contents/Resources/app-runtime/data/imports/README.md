# Manual Imports

Put optional local exports here when you want Personal Growth OS to include AI chat titles, TickTick tasks, health data, or notes.

Supported formats:

```csv
timestamp,source,type,topic,title,importance
2026-05-12T21:00:00+08:00,chatgpt,learning,"ai diary,life narrative",Personal Growth OS idea,0.9
```

You can optionally add `dimensions` to force a user-defined growth category:

```csv
timestamp,source,type,topic,title,importance,dimensions
2026-05-12T21:00:00+08:00,chatgpt,learning,"ai diary,life narrative",Personal Growth OS idea,0.9,personal_growth
```

```json
[
  {
    "timestamp": "2026-05-12T21:00:00+08:00",
    "source": "chatgpt",
    "type": "learning",
    "topic": ["ai diary", "life narrative"],
    "title": "Personal Growth OS idea",
    "importance": 0.9,
    "dimensions": ["personal_growth"]
  }
]
```

The generator reads these files locally and merges them with browser history. Keep sensitive items out, or mark them in a separate private file and do not import it.
