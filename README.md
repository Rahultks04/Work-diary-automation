# VTU Internship Work Diary Automation

Automates the daily VTU Internship Portal diary submission using **RAG + Gemini AI**. The script fetches your lesson content directly from the ISPARK curriculum API, generates a professional diary entry using Google Gemini, and fills in the VTU portal form automatically via Playwright browser automation.

---

## How It Works

```
ISPARK Curriculum API
        │
        ▼
  Lesson Content (HTML → plain text)
        │
        ▼
  Gemini 2.5 Flash Lite
        │
        ▼
  Generated Title + Summary
        │
        ▼
  Playwright (Chromium)
        │
        ▼
  VTU Internship Portal → Diary Form Filled
```

1. Prompts you for the diary date and lesson coordinates (phase / week / day / lesson)
2. Fetches the lesson from the ISPARK API and strips it to plain text
3. Sends the content to Gemini, which returns a one-line title and a ≤300-word summary
4. Logs into the VTU portal, navigates to the Internship Diary, and fills in:
   - Work Summary (Gemini title)
   - Learnings (Gemini summary)
   - Hours Worked (default: 4)
   - Skills Used (default: Python)
5. Leaves the browser open for you to review and submit manually

---

## Prerequisites

- Python 3.11+
- A Google Gemini API key → [Get one here](https://aistudio.google.com/app/apikey)
- Your VTU portal credentials (email + password)
- Your ISPARK bearer token and internship ID

---

## Installation

**1. Clone the repository**
```bash
git clone https://github.com/your-username/vtu-diary-automation.git
cd vtu-diary-automation
```

**2. Install dependencies**
```bash
pip install playwright google-generativeai requests beautifulsoup4 python-dotenv
playwright install chromium
```

**3. Create a `.env` file** in the project root:
```env
# VTU Portal credentials
EMAIL=your_vtu_email@example.com
PASSWORD=your_vtu_password

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key

# ISPARK API
ISPARK_TOKEN=your_ispark_bearer_token
ISPARK_INTERNSHIP_ID=your_ispark_internship_id
```

> ⚠️ Never commit your `.env` file. It is already included in `.gitignore` below.

---

## Usage

```bash
python vtu_diary_automation.py
```

You will be prompted for:

```
Date to enter in the diary (YYYY-MM-DD): 2026-04-10
Phase:   1
Week:    2
Day:     3
Lesson:  1
```

The browser will open, fill the form automatically, and wait. **Review the entries, then submit manually and close the browser.**

---

## Configuration

You can adjust these constants at the top of `vtu_diary_automation.py`:

| Variable | Default | Description |
|---|---|---|
| `HOURS_WORKED` | `"4"` | Hours to log for the day |
| `SKILL` | `"python"` | Skill tag to add in Skills Used |
| `HEADLESS` | `False` | Set `True` to run without a visible browser |

---

## Project Structure

```
vtu-diary-automation/
├── vtu_diary_automation.py   # Main automation script
├── .env                      # Your secrets (never commit this)
├── .gitignore
└── README.md
```

---

## .gitignore

Create a `.gitignore` with the following contents:

```
.env
__pycache__/
*.pyc
*.pyo
.DS_Store
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `playwright` | Browser automation (Chromium) |
| `google-generativeai` | Gemini API client |
| `requests` | ISPARK curriculum API calls |
| `beautifulsoup4` | Strip HTML from lesson content |
| `python-dotenv` | Load credentials from `.env` |

---

## Notes

- The VTU portal sometimes shows an "Important Notice" popup on login — the script dismisses it automatically.
- The date picker on the portal only allows past dates. Future dates are disabled and the script will raise a clear error if you pick one.
- The script uses `gemini-2.5-flash-lite` for fast, cost-effective generation. You can change the model in `summarise_with_gemini()`.
- The browser stays open indefinitely after filling the form. It will not close until you close it manually.

---

## License

MIT License — feel free to use and modify for your own internship portal.
