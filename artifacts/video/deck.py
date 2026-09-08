#!/usr/bin/env python3
"""Slide deck (PNG) for Devpost 'presentation' upload — static companion to the video.
Slides 4 (dashboard) and 5 (x402 section) come from the live dashboard, matching the video beats."""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8018/dashboard/index.html"
OUT = "/home/uwuki/sensormesh/artifacts/deck"

def shot(page, path, wait=900):
    page.wait_for_timeout(wait)
    page.screenshot(path=path)
    print("saved", path)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 900})
    for n in (1, 2, 3):
        pg.goto(f"file:///tmp/smv/slide-{n}.html")
        shot(pg, f"{OUT}/{n:02d}.png", 2600 if n in (2, 3) else 900)
    # 4: full dashboard with charts settled
    pg.goto(BASE)
    pg.wait_for_selector(".dataset-row", timeout=20000)
    shot(pg, f"{OUT}/04.png", 2500)
    # 5: x402 section after the flow lands (402 -> sign -> 200 + settlement)
    pg.locator(".x402-head").first.scroll_into_view_if_needed()
    pg.click("#buy")
    pg.wait_for_timeout(8000)
    pg.screenshot(path=f"{OUT}/05.png")
    print("saved", f"{OUT}/05.png")
    for n in (6, 7, 8):
        pg.goto(f"file:///tmp/smv/slide-{n}.html")
        shot(pg, f"{OUT}/{n:02d}.png")
    b.close()
print("deck done")
