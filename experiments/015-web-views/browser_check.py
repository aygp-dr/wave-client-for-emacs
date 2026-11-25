"""Drive system Chrome (headless, throwaway profile) through /app and /admin."""

import json
import sys

from playwright.sync_api import sync_playwright

BASE = "localhost:9896"
SCREENSHOT_DIR = sys.argv[1]
WAVE_ID = "localhost!w+g2x4"
GADGET_BLIP = "b+g2x4r3"
REPLY_TEXT = "browser-check reply from erin"
report = {}


def watch(page, label):
    messages = []
    page.on("console", lambda m: messages.append(f"{m.type}: {m.text}"))
    page.on("pageerror", lambda e: messages.append(f"pageerror: {e}"))
    page.on("requestfailed", lambda r: messages.append(f"requestfailed: {r.url} {r.failure}"))
    page.on("response", lambda r: r.status >= 400 and messages.append(f"http {r.status}: {r.url}"))
    report[label + "_console"] = messages


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="chrome", headless=True)
    report["chrome_version"] = browser.version

    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    watch(page, "app")
    page.goto(f"http://erin:erin@{BASE}/app")
    page.wait_for_selector(".wave-row")
    page.wait_for_selector(".topbar .me")
    report["app_me"] = page.inner_text(".topbar .me")
    report["app_folders"] = page.locator(".nav li").all_inner_texts()
    row = page.locator(f'.wave-row[data-wave-id="{WAVE_ID}"]')
    report["row_before_open"] = {"class": row.get_attribute("class"), "badge": row.locator(".badge").all_inner_texts()}
    row.click()
    page.wait_for_selector(".open-wave .blip")
    report["unread_blips_on_open"] = page.locator(".blip.unread").count()
    page.wait_for_function(
        f"""() => {{ const r = document.querySelector('.wave-row[data-wave-id="{WAVE_ID}"]');
                    return r && !r.querySelector('.badge'); }}""", timeout=5000)
    report["row_after_open"] = {"class": row.get_attribute("class"), "badge": row.locator(".badge").all_inner_texts()}
    report["participants"] = page.locator(".participants img").count()

    gadget = page.locator(f'.blip[data-blip-id="{GADGET_BLIP}"] table.gadget').first
    report["gadget_header_before"] = gadget.locator("thead th").all_inner_texts()
    gadget.locator('button[data-choice="yes"]').click()
    page.wait_for_function(
        f"""() => {{ const b = document.querySelector('.blip[data-blip-id="{GADGET_BLIP}"] button[data-choice="yes"]');
                    return b && b.classList.contains('chosen'); }}""", timeout=5000)
    report["gadget_header_after"] = gadget.locator("thead th").all_inner_texts()
    report["gadget_yes_voters"] = [img.get_attribute("title") for img in gadget.locator("tbody tr").first.locator("td").first.locator("img").all()]

    target = page.locator(f'.blip[data-blip-id="{GADGET_BLIP}"]')
    target.locator(":scope > .blip-actions button").click()
    target.locator(":scope > .reply-box textarea").fill(REPLY_TEXT)
    target.locator(":scope > .reply-box button.primary").click()
    page.wait_for_selector(f'.blip[data-blip-id="{GADGET_BLIP}"] > .thread .blip-body p:text("{REPLY_TEXT}")', timeout=5000)
    report["reply_nested_under"] = page.evaluate(
        f"""() => [...document.querySelectorAll('.blip-body p')].filter(p => p.textContent === {json.dumps(REPLY_TEXT)})
                   .map(p => p.closest('.thread').closest('.blip').dataset.blipId)""")

    page.locator('button[data-action="archive"]').click()
    page.wait_for_function(
        f"""() => !document.querySelector('.wave-row[data-wave-id="{WAVE_ID}"]')""", timeout=5000)
    report["archive_removed_from_inbox"] = True
    page.locator('button[data-action="unarchive"]').click()
    page.wait_for_selector(f'.wave-row[data-wave-id="{WAVE_ID}"]', timeout=5000)
    report["unarchive_returned_to_inbox"] = True
    page.wait_for_timeout(500)
    page.screenshot(path=f"{SCREENSHOT_DIR}/web-app.png")
    report["page_url_has_userinfo_in_location_href"] = page.evaluate("() => location.href.includes('erin:erin')")

    admin_context = browser.new_context(viewport={"width": 1440, "height": 900})
    admin_page = admin_context.new_page()
    watch(admin_page, "admin")
    admin_page.goto(f"http://admin:admin@{BASE}/admin")
    admin_page.wait_for_selector("table.data tr.clickable")
    admin_page.wait_for_function("() => document.querySelector('.stat b').textContent !== '…'")
    report["admin_stats"] = admin_page.locator(".stat").all_inner_texts()
    report["admin_user_rows"] = admin_page.locator("section:has(h2:text-matches('Users')) tbody tr").count()
    report["admin_wave_rows"] = admin_page.locator("tr.clickable").count()
    admin_page.locator(f'tr.clickable[data-wave-id="{WAVE_ID}"]').click()
    admin_page.wait_for_selector("pre.raw")
    raw = json.loads(admin_page.inner_text("pre.raw"))
    report["admin_raw_wavelets"] = len(raw)
    report["admin_raw_has_reply"] = any(REPLY_TEXT in json.dumps(w["docs"]) for w in raw)
    admin_page.screenshot(path=f"{SCREENSHOT_DIR}/web-admin.png", full_page=True)

    wrong_context = browser.new_context()
    wrong_page = wrong_context.new_page()
    try:
        response = wrong_page.goto(f"http://erin:erin@{BASE}/admin")
        report["user_creds_on_admin"] = response.status
    except Exception as error:  # Chrome rejects the 401 for URL-supplied creds
        report["user_creds_on_admin"] = str(error).splitlines()[0]
    browser.close()

print(json.dumps(report, indent=2))
