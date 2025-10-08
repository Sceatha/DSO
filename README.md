# DSO Visibility Browser

A lightweight **Streamlit app** for browsing deep-sky objects (DSOs) and notable stars that are **optimally visible** in a selected month, using a local SQLite database. You can filter by catalogue/type, search by text, view results by 2-hour blocks (with SDT/DST conversions), and export to CSV.

---

## 🧰 Requirements

- Python 3.9+ (recommended)
- Packages:  
  ```bash
  pip install streamlit pandas
  ```
- `sqlite3` and `os` are part of the Python standard library.

---

## 🚀 Quick Start

1. Clone or copy this repository.
2. Ensure you have a valid SQLite database.
3. Run the app:

   ```bash
   streamlit run DSOapp.py
   ```

4. Open the link shown in the terminal (usually http://localhost:8501).

By default, the app looks for a database at `data/DSO.db`. You can change the path in the **left sidebar** (“SQLite DB path”).  
If the file doesn’t exist, the app shows an informational message and stops gracefully.

---

## 🌌 App Features

- **Database validation** — checks for required tables and columns.
- **Month selector (1–12)** — drives which constellations are “optimal” that month.
- **Time mode** — toggle between Standard and Daylight Saving to adjust hour labels:
  - Standard: 1→21:00 SDT, 2→23:00 SDT, 3→01:00 SDT, 4→03:00 SDT  
  - Daylight: 1→22:00 DST, 2→00:00 DST, 3→02:00 DST, 4→04:00 DST
- **Search bar** — case-insensitive contains match on Name/Type/Constellation.
- **Catalogue filters** — Messier, Caldwell, or “Other” (anything not those two).
- **Star type filters** — Double Star, Red Giant, or “Others”.
- **Tabbed view by Hour** — four 2-hour blocks (1–4).
- **Two result tables per hour tab**:
  - *DSO Results*: Constellation, Code, Type, Name, Notes  
    (rows with entry in *Turn Left at Orion* are softly highlighted)
  - *Star Results*: Constellation, Code, Type, Name, Stars, Notes
- **CSV export** — download filtered results for each table.
- **Sidebar info** — displays match counts for DSOs and stars.

## 💡 Usage Tips

- **DB Path** — Put your database at `data/DSO.db` or update the sidebar field.
- **Flexible columns** — Case/space differences in column names are tolerated.
- **Performance** — Streamlit caches the DB connection; restart if you update the DB file.
- **Export** — Use sidebar buttons to download CSVs.

---

## 🧱 Project Structure

```
.
├─ DSOapp.py        # Streamlit app
└─ data/
   └─ DSO.db        # Your SQLite database (not included)
```

---

## 🧠 Troubleshooting

| Problem | Cause / Fix |
|:--|:--|
| “Database file not found” | The provided path doesn’t exist. Check the sidebar. |
| “Schema check failed” | Create the missing tables/columns listed above. |
| Empty results | Ensure `Visibility` has rows for the selected month and `Optimal = 1`. Also check that at least one filter (catalogue/star type) is active. |

---

## ⚙️ Developer Notes

- **Data joins** are case-insensitive and ignore whitespace around `Constellation`.
- **UI polish** — Column widths and table heights are auto-sized for readability.
- **Hour tabs** — Cosmetic labels are controlled via the `hour_fixer()` function.

---

## 🕓 Changelog

- **v1.0** — Initial release.
