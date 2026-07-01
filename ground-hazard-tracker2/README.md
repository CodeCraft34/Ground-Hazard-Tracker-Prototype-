# Ground Hazard Tracker — Setup Guide (Mobile / Replit)

## 1. Create the Replit project
1. Open the Replit app (or replit.com in your phone browser).
2. Tap **+ Create Repl**.
3. Choose template **Python**. Name it `ground-hazard-tracker`. Tap **Create Repl**.

## 2. Add the files
You only need to create 4 files/folders. In Replit's mobile file panel, tap the
**+ file** icon for each one and paste the matching content from this package:

- `main.py` → paste contents of `main.py`
- `requirements.txt` → paste contents of `requirements.txt`
- `.replit` → tap **+ file**, name it exactly `.replit`, paste contents of `.replit`
  (this makes the Run button start the server automatically)
- `static/index.html` → first create a folder named `static` (tap **+ folder**),
  then inside it create `index.html` and paste the contents

You do **not** need to manually create `static/uploads` — the app creates it
automatically the first time it starts.

## 3. Install dependencies
Replit usually auto-installs from `requirements.txt` the first time you hit Run.
If it doesn't, open the **Shell** tab and run:
```
pip install -r requirements.txt
```

## 4. Run it
Tap the big green **Run** button. Replit will start the server and open a
webview panel showing your app (it's calling `uvicorn` on port 8080 under the hood).

## 5. Test on your phone
- Tap **Continue as Guest** (or enter any username/password — login is just a
  prototype gate, not real auth).
- Allow location access when your phone prompts you.
  - Replit's webview/preview URL is HTTPS, so real GPS should work.
  - If it's blocked, the app shows a yellow bar with manual **Latitude/Longitude**
    boxes — type in any coordinates and tap **Set Location** to simulate being
    somewhere else (use this to test the 5km warning radius from different spots).
- Fill out the **Report an Issue** form (pick a type, write a description, choose
  a photo from your phone gallery) and tap **Submit Report**.
- Watch the map drop a new pin and the feed card appear instantly below.
- Open the app in a second browser tab/device with different manual coordinates
  to see the red "CRITICAL WARNING" banner trigger when a hazard is within 5km.

## 6. Where things live
- Database: `hazards.db` (SQLite file, created automatically, sits in project root)
- Uploaded photos: `static/uploads/` (served at `/static/uploads/<filename>`)
- Everything resets if you delete `hazards.db` — handy for demo resets.

## 7. Common mobile gotchas
- If Tailwind/Leaflet/jQuery don't load, check Replit's webview has internet
  access (it should by default) — all three are loaded from public CDNs.
- If photo upload fails, double check you selected an image file type
  (`.jpg`, `.png`, etc.) — the input is restricted to `accept="image/*"`.
- If the Run button shows a port error, just tap Run again — Replit sometimes
  needs a second to bind the port after a fresh install.
