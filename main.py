import requests
import os
import json
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import datetime

# -----------------------------
# LOAD ENV
# -----------------------------
load_dotenv()

ISPARK_TOKEN = os.getenv("ISPARK_TOKEN")
ISPARK_INTERNSHIP_ID = os.getenv("ISPARK_INTERNSHIP_ID")

VTU_TOKEN = os.getenv("VTU_TOKEN")
VTU_INTERNSHIP_ID = int(os.getenv("VTU_INTERNSHIP_ID"))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# -----------------------------
# HEADERS
# -----------------------------
ispark_headers = {
    "Authorization": f"Bearer {ISPARK_TOKEN}",
    "User-Agent": "Mozilla/5.0"
}

vtu_headers = {
    "Authorization": f"Bearer {VTU_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://vtu.internyet.in",
    "Referer": "https://vtu.internyet.in/"
}

# -----------------------------
# USER INPUT
# -----------------------------
phase = int(input("Phase: "))
week = int(input("Week: "))
day = int(input("Day: "))
lesson = int(input("Lesson: "))

print("\nEnter diary date (YYYY-MM-DD)")
user_date = input("Date: ")

try:
    datetime.strptime(user_date, "%Y-%m-%d")
except ValueError:
    print("Invalid date format.")
    exit()

# -----------------------------
# FETCH LESSON
# -----------------------------
print("\nFetching lesson...")

url = f"https://isparkskills.ai/api/curriculum/{ISPARK_INTERNSHIP_ID}"

res = requests.get(url, headers=ispark_headers)

if res.status_code != 200:
    print("Failed to fetch curriculum")
    exit()

data = res.json()

lesson_data = data["curriculum"][phase-1]["weeks"][week-1]["days"][day-1]["lessons"][lesson-1]

title = lesson_data["title"]
html = lesson_data["content"]

soup = BeautifulSoup(html, "html.parser")
text = soup.get_text()

text = text[:6000]

print("Lesson:", title)

# -----------------------------
# GEMINI API (WORKING)
# -----------------------------
print("\nGenerating diary using Gemini...")

gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GOOGLE_API_KEY}"

prompt = f"""
Write a VTU internship diary entry.

Return STRICT JSON only:

{{
"summary":"",
"learnings":"",
"blockers":""
}}

Lesson content:
{text}
"""

payload = {
    "contents": [
        {
            "parts": [
                {"text": prompt}
            ]
        }
    ]
}

response = requests.post(gemini_url, json=payload)

result = response.json()

# Debug if needed
# print(result)

try:
    raw = result["candidates"][0]["content"]["parts"][0]["text"]
except:
    print("\nGemini API Error:\n")
    print(result)
    exit()

raw = raw.strip()

# Clean markdown if present
raw = re.sub(r"^```json", "", raw)
raw = re.sub(r"```$", "", raw)
raw = raw.strip()

try:
    parsed = json.loads(raw)
except:
    print("\nGemini returned invalid JSON:\n")
    print(raw)
    exit()

summary = parsed.get("summary", "")
learnings = parsed.get("learnings", "")
blockers = parsed.get("blockers", "")

# -----------------------------
# FORMAT FIX
# -----------------------------
if isinstance(learnings, list):
    learnings = "\n\n".join(learnings)

if isinstance(blockers, list):
    blockers = "\n\n".join(blockers)

summary = summary[:1000]

print("\nGenerated Summary:\n")
print(summary)

# -----------------------------
# FETCH SKILLS
# -----------------------------
print("\nFetching skills...")

skills_url = "https://vtuapi.internyet.in/api/v1/master/skills"

skills_res = requests.get(skills_url, headers=vtu_headers)

skills_data = skills_res.json()

skill_ids = []

for skill in skills_data["data"]:
    name = skill["name"].lower()

    if "python" in name:
        skill_ids.append(str(skill["id"]))

    if "machine learning" in name:
        skill_ids.append(str(skill["id"]))

if not skill_ids:
    skill_ids = ["3"]

print("Using skills:", skill_ids)

# -----------------------------
# SUBMIT DIARY
# -----------------------------
payload = {
    "internship_id": VTU_INTERNSHIP_ID,
    "date": user_date,
    "description": summary,
    "hours": 6,
    "links": "",
    "blockers": blockers,
    "learnings": learnings,
    "mood_slider": 5,
    "skill_ids": skill_ids
}

print("\nPayload being sent:\n")
print(json.dumps(payload, indent=2))

submit_url = "https://vtuapi.internyet.in/api/v1/student/internship-diaries/store"

print("\nSubmitting diary...")

r = requests.post(submit_url, json=payload, headers=vtu_headers)

print("\nVTU Response:")
print(r.json())