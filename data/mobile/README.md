# Mobile Browsing Imports

Use this folder for phone-side browsing records from Bilibili, Zhihu, Xiaohongshu, CSDN, or other apps.

Directly reading mobile app histories from the computer is usually not reliable unless the app syncs data to a local desktop database. For MVP, export or manually collect day-level/title-level records into CSV or JSON.

CSV template:

```csv
timestamp,platform,title,duration_minutes,url,importance
2026-05-12T22:10:00+08:00,bilibili,李宏毅深度学习课程 Regression,18,https://www.bilibili.com/video/example,0.65
2026-05-12T22:35:00+08:00,zhihu,如何选择计算所导师,6,,0.55
2026-05-12T23:00:00+08:00,xiaohongshu,夏令营申请经验,8,,0.5
```

JSON template:

```json
[
  {
    "timestamp": "2026-05-12T22:10:00+08:00",
    "platform": "bilibili",
    "title": "李宏毅深度学习课程 Regression",
    "duration_minutes": 18,
    "url": "https://www.bilibili.com/video/example",
    "importance": 0.65
  }
]
```

Supported platform labels include `bilibili`, `zhihu`, `xiaohongshu`, `csdn`, `wechat_article`, and any custom label you want.
