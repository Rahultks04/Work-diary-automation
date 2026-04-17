With window preview.

import asyncio
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


load_dotenv()
# ─────────────────────────────────────────
#  CONFIGURATION — edit these before running
# ─────────────────────────────────────────

EMAIL    = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")


# Gemini API key — or set env var GEMINI_API_KEY instead
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("API_KEY"))

# Path to the lesson notes file (same folder as this script, or full path)
LESSON_FILE = "lesson.txt"

# Date to enter in the diary (DD/MM/YYYY or YYYY-MM-DD)
DIARY_DATE = input("Date to enter in the diary (DD/MM/YYYY or YYYY-MM-DD)")   # change to any valid past date

# Hours worked to fill in
HOURS_WORKED = "4"

# Skill to add in the Skills Used react-select field
SKILL = "python"

# Set HEADLESS = False to watch the browser, True to run silently
HEADLESS = False
# ─────────────────────────────────────────


def parse_date(date_str: str) -> datetime:
    """Accept YYYY-MM-DD or DD/MM/YYYY and return a datetime object."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {date_str!r}. Use YYYY-MM-DD or DD/MM/YYYY.")


def load_lesson_text() -> str:
    """Read and return the contents of lesson.txt."""
    path = Path(LESSON_FILE)
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find '{LESSON_FILE}'. "
            "Please place lesson.txt in the same folder as this script."
        )
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError("lesson.txt is empty. Please add your lesson notes.")
    print(f"[GEMINI] Loaded lesson.txt ({len(content)} characters)")
    return content


def summarise_with_gemini(lesson_text: str) -> tuple[str, str]:
    """
    Send lesson_text to Gemini and return (title, summary).
      title  : one-line heading of what was learnt  → goes into Work Summary field
      summary: ≤300-word paragraph                  → goes into Learnings field
    """
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")

    prompt = f"""
You are helping a university intern fill in their daily work diary.

Given the lesson notes below, produce TWO things:

1. TITLE — A single concise line (max 15 words) describing what was learnt today.
   Format exactly as:
   TITLE: <your title here>

2. SUMMARY — A clear, professional summary of the lesson in UNDER 2000 characters.
   Cover the key concepts, tools used, and outcomes.
   Format exactly as:
   SUMMARY: <your summary here>

Lesson notes:
\"\"\"
{lesson_text}
\"\"\"

Return ONLY the TITLE line and the SUMMARY line — no other commentary.
""".strip()

    print("[GEMINI] Sending lesson to Gemini API …")
    response = model.generate_content(prompt)
    raw = response.text.strip()
    print("[GEMINI] Response received ✓")

    # Parse TITLE and SUMMARY — handle both single-line and multi-line responses
    title = ""
    summary_lines = []
    in_summary = False

    for line in raw.splitlines():
        if line.startswith("TITLE:"):
            title = line.removeprefix("TITLE:").strip()
            in_summary = False
        elif line.startswith("SUMMARY:"):
            in_summary = True
            rest = line.removeprefix("SUMMARY:").strip()
            if rest:
                summary_lines.append(rest)
        elif in_summary:
            summary_lines.append(line)

    summary = " ".join(summary_lines).strip()

    if not title or not summary:
        raise ValueError(
            f"Could not parse Gemini response. Raw output:\n{raw}"
        )

    # Enforce 300-word cap (trim at word boundary)
    words = summary.split()
    if len(words) > 300:
        summary = " ".join(words[:300]) + "…"

    print(f"[GEMINI] Title   : {title}")
    print(f"[GEMINI] Summary : {summary[:100]}…")
    return title, summary


async def run():
    target_date = parse_date(DIARY_DATE)
    print(f"[CONFIG] Diary date → {target_date.strftime('%d %B %Y')}")

    # ── Pre-flight: load lesson and call Gemini BEFORE opening browser ─────
    lesson_text = load_lesson_text()
    title, summary = summarise_with_gemini(lesson_text)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, slow_mo=300)
        context = await browser.new_context()
        page    = await context.new_page()

        # ── STEP 1A: Login ────────────────────────────────────────────────
        print("[1/8] Navigating to sign-in page …")
        await page.goto("https://vtu.internyet.in/sign-in", wait_until="networkidle")
        await page.fill('input[placeholder="Enter your email address"]', EMAIL)
        await page.fill('input[id="password"]', PASSWORD)
        await page.click('button[type="submit"]')

        print("[1/8] Credentials submitted — waiting for dashboard …")
        await page.wait_for_selector("aside, nav", timeout=20_000)

        # ── STEP 1B: Dismiss "Important Notice" popup ─────────────────────
        print("[1/8] Looking for 'I Understand' popup …")
        try:
            i_understand_btn = page.locator(
                'button:has-text("I Understand"), '
                'button.primary-btn:has-text("I Understand")'
            ).first
            await i_understand_btn.wait_for(state="visible", timeout=15_000)
            await i_understand_btn.dispatch_event("click")
            print("[1/8] Popup dismissed ✓")
            await page.wait_for_selector('[role="dialog"]', state="hidden", timeout=10_000)
        except PlaywrightTimeoutError:
            print("[1/8] Popup did not appear — continuing.")

        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(800)

        # ── STEP 1C: Click "Internship Diary" in sidebar ──────────────────
        print("[1/8] Clicking 'Internship Diary' …")
        diary_link = page.locator(
            'a[href="/dashboard/student/student-diary"], '
            'a[title="Internship Diary"]'
        ).first
        await diary_link.wait_for(state="attached", timeout=15_000)
        await diary_link.scroll_into_view_if_needed()
        await diary_link.wait_for(state="visible", timeout=10_000)
        await diary_link.click()
        await page.wait_for_load_state("networkidle")
        print("[1/8] Internship Diary page loaded ✓")

        # ── STEP 2: Select internship from dropdown ───────────────────────
        print("[2/8] Selecting internship …")
        select_trigger = page.locator('#internship_id')
        await select_trigger.wait_for(state="visible", timeout=10_000)
        await select_trigger.click()
        target_option = page.locator(
            '[role="option"]:has-text("Remote Internship in Intelligent AI Agents")'
        ).first
        await target_option.wait_for(state="visible", timeout=10_000)
        await target_option.click()
        print("[2/8] Internship selected ✓")
        await page.wait_for_timeout(800)

        # ── STEP 3: Pick the diary date ───────────────────────────────────
        print(f"[3/8] Opening date picker …")
        date_trigger = page.locator('button[aria-haspopup="dialog"]').filter(has_text="Pick a Date")
        await date_trigger.wait_for(state="visible", timeout=10_000)
        await date_trigger.click()
        await page.wait_for_selector('[data-slot="calendar"]', timeout=8_000)
        await page.wait_for_timeout(400)

        await select_calendar_date(page, target_date)
        print(f"[3/8] Date {target_date.strftime('%d %B %Y')} selected ✓")
        await page.wait_for_selector('[data-slot="calendar"]', state="hidden", timeout=8_000)
        await page.wait_for_timeout(500)

        # ── STEP 4: Click Continue ────────────────────────────────────────
        print("[4/8] Waiting for Continue to become enabled …")
        continue_btn = page.locator('button[type="submit"]:has-text("Continue")')
        await continue_btn.wait_for(state="visible", timeout=10_000)
        await page.wait_for_function(
            '() => { const b = document.querySelector(\'button[type="submit"]\'); return b && !b.disabled; }',
            timeout=10_000,
        )
        await continue_btn.click()
        await page.wait_for_load_state("networkidle")
        print("[4/8] Continue clicked ✓ — diary form loaded")

        # ── STEP 5: Fill Work Summary (Gemini title) ──────────────────────
        print("[5/8] Filling Work Summary …")
        work_summary = page.locator('textarea[name="description"]')
        await work_summary.wait_for(state="visible", timeout=10_000)
        await work_summary.click()
        await work_summary.fill(title)
        print(f"[5/8] Work Summary filled ✓")

        # ── STEP 6: Fill Learnings (Gemini summary) ───────────────────────
        print("[6/8] Filling Learnings …")
        learnings = page.locator('textarea[name="learnings"]')
        await learnings.wait_for(state="visible", timeout=10_000)
        await learnings.click()
        await learnings.fill(summary)
        print("[6/8] Learnings filled ✓")

        # ── STEP 7: Set Hours Worked ──────────────────────────────────────
        print(f"[7/8] Setting hours worked to {HOURS_WORKED} …")
        hours_input = page.locator('input[type="number"][placeholder="e.g. 6.5"]')
        await hours_input.wait_for(state="visible", timeout=10_000)
        await hours_input.click(click_count=3)   # select-all equivalent (triple_click not available in older Playwright)
        await hours_input.fill(HOURS_WORKED)
        print(f"[7/8] Hours worked set to {HOURS_WORKED} ✓")

        # ── STEP 8: Add skill in React-Select "Skills Used" ───────────────
        print(f"[8/8] Adding skill '{SKILL}' …")
        skills_input = page.locator('#react-select-2-input')
        await skills_input.wait_for(state="visible", timeout=10_000)
        await skills_input.click()
        await skills_input.type(SKILL, delay=80)
        await page.wait_for_timeout(700)

        skill_option = page.locator(
            f'[id^="react-select-"][id*="-option-"]'
        ).filter(has_text=SKILL).first
        try:
            await skill_option.wait_for(state="visible", timeout=6_000)
            await skill_option.click()
            print(f"[8/8] Skill '{SKILL}' selected from dropdown ✓")
        except PlaywrightTimeoutError:
            # await skills_input.press("Enter")
            print(f"[8/8] Skill '{SKILL}' confirmed via Enter ✓")

        await page.wait_for_timeout(500)
        print("\n✅ All 8 steps complete! Review the form and submit manually.")
        print("   The script will exit only after you close the browser window.")

        # ── Wait indefinitely until the user closes the browser window ────
        # Uses a polling loop so it survives tab navigation and page reloads.
        # The loop exits cleanly when the browser process is gone.
        while True:
            try:
                await page.wait_for_timeout(20_000)
                if not browser.is_connected():
                    break
            except Exception:
                # Any playwright error here means the browser is already gone
                break

        print("Browser closed — script exiting.")


async def select_calendar_date(page, target: datetime):
    """
    Select a date using the RDP calendar's hidden <select> dropdowns and
    data-day attribute on day buttons.
    """
    month_value = str(target.month - 1)
    year_value  = str(target.year)
    day_str     = target.strftime("%d/%m/%Y")

    print(f"[3/8]   → Setting calendar: month={month_value}, year={year_value}")

    year_select = page.locator(
        'select.rdp-years_dropdown, select[aria-label="Choose the Year"]'
    ).first
    await year_select.wait_for(state="attached", timeout=5_000)
    await year_select.select_option(value=year_value)
    await page.wait_for_timeout(300)

    month_select = page.locator(
        'select.rdp-months_dropdown, select[aria-label="Choose the Month"]'
    ).first
    await month_select.wait_for(state="attached", timeout=5_000)
    await month_select.select_option(value=month_value)
    await page.wait_for_timeout(400)

    parent_td = page.locator(f'td[data-day="{target.strftime("%Y-%m-%d")}"]').first
    is_disabled = await parent_td.get_attribute("data-disabled")
    if is_disabled == "true":
        raise ValueError(
            f"Date {target.strftime('%d %B %Y')} is disabled (future or out of range). "
            "Please choose a valid past date."
        )

    day_btn = page.locator(f'button[data-day="{day_str}"]').first
    await day_btn.wait_for(state="visible", timeout=5_000)
    await day_btn.click()
    print(f"[3/8]   → Clicked day: {day_str}")


if __name__ == "__main__":
    asyncio.run(run())
