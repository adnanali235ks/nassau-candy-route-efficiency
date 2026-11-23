"""
Capture genuine, fully rendered, full-page browser screenshots of every dashboard page, and test the
download buttons by really clicking them.

Optional developer tool (not needed to run the dashboard). Uses Microsoft Edge (installed with Windows) in headless
mode, controlled over the Chrome DevTools Protocol with the `websockets` package. `websockets` is installed together with
recent Streamlit versions (it was present with Streamlit 1.67); if it is missing, run `pip install websockets`.

Usage (the app must already be running, e.g. `streamlit run app.py --server.port 8503`):
    python tools/capture_screenshots.py --url http://localhost:8503 --out docs/screenshots

How "fully rendered" is decided: a page is captured only after (1) its title is on screen, (2) Streamlit's
"running" indicator and loading skeletons are gone, (3) the expected number of charts / download buttons exist,
and (4) this state has been stable for several consecutive checks. The viewport is then made as tall as the content.
"""

import argparse
import asyncio
import base64
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

from websockets.asyncio.client import connect

EDGE_CANDIDATES = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                   r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
WIDTH = 1500

# page url path -> (expected h1 text, minimum plotly charts, minimum download buttons)
PAGES = {
    "executive_overview": ("", "Executive Overview", 4, 0),
    "geographic_analysis": ("geographic_analysis", "Geographic Analysis", 1, 0),
    "route_performance": ("route_performance", "Route Performance", 2, 0),
    "optimization_center": ("optimization_center", "Optimization Center", 1, 2),
    "scenario_simulator": ("scenario_simulator", "Scenario Simulator", 2, 0),
    "smart_recommendations": ("smart_recommendations", "Smart Recommendations", 0, 1),
    "anomaly_detection": ("anomaly_detection", "Anomaly Detection", 0, 1),
    "reports": ("reports", "Reports", 0, 3),
}

STATE_JS = """(() => {
  const q = s => document.querySelectorAll(s).length;
  const main = document.querySelector('[data-testid="stMain"]') || document.querySelector('section.main');
  const h1 = main ? main.querySelector('h1') : null;      // the page title (the sidebar has its own h1)
  return JSON.stringify({
    running: q('[data-testid="stStatusWidget"]') > 0,
    skeleton: q('[data-testid="stSkeleton"]') + q('[class*="stSkeleton"]'),
    h1: h1 ? h1.innerText : null,
    charts: q('.js-plotly-plot'),
    downloads: q('[data-testid="stDownloadButton"]'),
    exceptions: q('[data-testid="stException"]'),
    height: main ? main.scrollHeight : 0,
    sidebar: (document.querySelector('[data-testid="stSidebarContent"]') || {scrollHeight: 0}).scrollHeight,
  });
})()"""


class Cdp:
    def __init__(self, ws):
        self.ws, self.n = ws, 0

    async def call(self, method, params=None, timeout=60):
        self.n += 1
        msg_id = self.n
        await self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        while True:
            reply = json.loads(await asyncio.wait_for(self.ws.recv(), timeout))
            if reply.get("id") == msg_id:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error']}")
                return reply.get("result", {})

    async def js(self, expression):
        result = await self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        return result.get("result", {}).get("value")


async def page_state(cdp):
    raw = await cdp.js(STATE_JS)
    return json.loads(raw) if raw else {}


async def wait_rendered(cdp, title, min_charts, min_downloads, timeout=180, stable_checks=4):
    """Wait until the page is completely rendered and stable. Returns the final state."""
    t0, stable, last = time.time(), 0, None
    while time.time() - t0 < timeout:
        s = await page_state(cdp)
        ok = (s.get("h1") and title in s["h1"] and not s["running"] and s["skeleton"] == 0
              and s["charts"] >= min_charts and s["downloads"] >= min_downloads and s["exceptions"] == 0)
        key = (s.get("charts"), s.get("downloads"), s.get("height"))
        stable = stable + 1 if ok and key == last else 0
        last = key
        if stable >= stable_checks:
            return s
        await asyncio.sleep(1.0)
    raise TimeoutError(f"page '{title}' did not finish rendering; last state: {last} / {await page_state(cdp)}")


async def full_page_screenshot(cdp, path, title, min_charts, min_downloads):
    s = await page_state(cdp)
    height = int(min(max(s.get("height", 0), s.get("sidebar", 0), 900) + 140, 16000))
    await cdp.call("Emulation.setDeviceMetricsOverride",
                   {"width": WIDTH, "height": height, "deviceScaleFactor": 1, "mobile": False})
    await asyncio.sleep(2.0)                                   # let Streamlit and Plotly re-layout at the new size
    s = await wait_rendered(cdp, title, min_charts, min_downloads, timeout=90)
    height = int(min(max(s.get("height", 0), s.get("sidebar", 0), 900) + 140, 16000))
    await cdp.call("Emulation.setDeviceMetricsOverride",
                   {"width": WIDTH, "height": height, "deviceScaleFactor": 1, "mobile": False})
    await asyncio.sleep(1.0)
    shot = await cdp.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
    pathlib.Path(path).write_bytes(base64.b64decode(shot["data"]))
    return s, height


async def click_text(cdp, selector, text):
    """Click the first element matching `selector` whose text contains `text`. Returns True if clicked."""
    expr = (f"(() => {{ const el = [...document.querySelectorAll({json.dumps(selector)})]"
            f".find(e => e.innerText && e.innerText.includes({json.dumps(text)})); "
            f"if (!el) return false; el.click(); return true; }})()")
    return bool(await cdp.js(expr))


async def navigate(cdp, url):
    await cdp.call("Page.navigate", {"url": url})
    await asyncio.sleep(2.0)


def check_download(path):
    """Return a short description if the downloaded file looks valid, else raise."""
    data = path.read_bytes()
    name = path.name.lower()
    if name.endswith(".pdf"):
        assert data.startswith(b"%PDF-") and b"%%EOF" in data[-1024:], "not a valid PDF"
        return f"PDF, {len(data) // 1024} KB"
    if name.endswith(".xlsx"):
        from openpyxl import load_workbook
        wb = load_workbook(path)
        assert wb.sheetnames[0] == "Executive Summary" and len(wb.sheetnames) == 9, wb.sheetnames
        return f"Excel, {len(wb.sheetnames)} sheets, {len(data) // 1024} KB"
    if name.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            return f"ZIP, {len(z.namelist())} CSV files"
    if name.endswith(".csv"):
        assert len(data) > 20 and b"," in data
        return f"CSV, {len(data) // 1024} KB, {data.count(b'\n')} lines"
    return f"{len(data)} bytes"


async def run(args):
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    downloads = pathlib.Path(tempfile.mkdtemp(prefix="dl_"))
    profile = tempfile.mkdtemp(prefix="edge_profile_")
    edge = args.edge or next((p for p in EDGE_CANDIDATES if os.path.exists(p)), None)
    if not edge:
        sys.exit("Microsoft Edge was not found; pass --edge PATH")
    port = args.port
    proc = subprocess.Popen([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--remote-debugging-port={port}",
                             f"--user-data-dir={profile}", f"--window-size={WIDTH},1000", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = {"screenshots": {}, "downloads": {}}
    try:
        for _ in range(60):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                page_ws = next(t["webSocketDebuggerUrl"] for t in targets if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.5)
        else:
            sys.exit("Could not connect to Edge's debugging port")
        version = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version"))
        async with connect(page_ws, max_size=None) as ws, connect(version["webSocketDebuggerUrl"], max_size=None) as bws:
            cdp, browser = Cdp(ws), Cdp(bws)
            await browser.call("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(downloads)})
            await cdp.call("Page.enable")
            await cdp.call("Runtime.enable")

            for name, (path, title, charts, dls) in PAGES.items():
                if args.only and name not in args.only:
                    continue
                await cdp.call("Emulation.setDeviceMetricsOverride", {"width": WIDTH, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
                await navigate(cdp, f"{args.url.rstrip('/')}/{path}")
                # the Reports downloads only exist after "Generate reports" is pressed, so do not wait for them yet
                await wait_rendered(cdp, title, charts, 0 if name == "reports" else dls)

                if name == "reports":                              # press the button, then wait for the three downloads
                    assert await click_text(cdp, "button", "Generate reports"), "Generate reports button not found"
                    await asyncio.sleep(2.0)
                    charts, dls = 0, 3
                    await wait_rendered(cdp, title, charts, dls, timeout=240)
                if name == "smart_recommendations":                # open two recommendations so Why / Rule / Values are visible
                    for label in ("R01 ·", "R07 ·"):                # two different entries (clicking one twice would close it)
                        assert await click_text(cdp, "summary", label), f"recommendation {label} not found"
                        await asyncio.sleep(0.8)
                    await wait_rendered(cdp, title, charts, dls)

                s, h = await full_page_screenshot(cdp, out / f"{name}.png", title, charts, dls)
                results["screenshots"][name] = {"height_px": h, "charts": s["charts"], "download_buttons": s["downloads"]}
                print(f"captured {name}.png  height={h}px charts={s['charts']} downloads={s['downloads']}", flush=True)

                # --- click every download button on the page and verify the files ---
                if s["downloads"]:
                    for old in downloads.iterdir():            # start each page with an empty folder so same-named files are not missed
                        old.unlink()
                    before = set()
                    count = int(await cdp.js("document.querySelectorAll('[data-testid=\"stDownloadButton\"]').length"))
                    for i in range(count):
                        await cdp.js(f"(() => {{ const b = document.querySelectorAll('[data-testid=\"stDownloadButton\"]')[{i}]; "
                                     "const t = b.querySelector('button') || b.querySelector('a') || b; t.click(); })()")
                        await asyncio.sleep(1.2)
                    await asyncio.sleep(3.0)
                    new = sorted(p for p in downloads.iterdir() if p.name not in before and not p.name.endswith(".crdownload"))
                    results["downloads"][name] = {}
                    for p in new:
                        results["downloads"][name][p.name] = check_download(p)
                    results["downloads"][name]["_buttons_clicked"] = count
                    results["downloads"][name]["_files_received"] = len(new)
                    print(f"  downloads on {name}: clicked {count}, received {len(new)} -> "
                          + "; ".join(f"{k}: {v}" for k, v in results['downloads'][name].items() if not k.startswith('_')), flush=True)

            # extra tab screenshots (the first tab of each page is the default capture above)
            for page, tabs in (("geographic_analysis", [("Distance comparison", "distance"), ("Shipment density", "density")]),
                               ("route_performance", [("Ship mode comparison", "ship_modes"), ("drill-down", "drilldown")]),
                               ("anomaly_detection", [("Duplicate lines", "duplicates")])):
                if args.only and page not in args.only:
                    continue
                path, title, charts, dls = PAGES[page]
                await navigate(cdp, f"{args.url.rstrip('/')}/{path}")
                await wait_rendered(cdp, title, 0, 0)
                for label, suffix in tabs:
                    assert await click_text(cdp, '[role="tab"]', label), f"tab {label} not found on {page}"
                    await asyncio.sleep(3.0)
                    await wait_rendered(cdp, title, 0, 0)
                    s, h = await full_page_screenshot(cdp, out / f"{page}_{suffix}.png", title, 0, 0)
                    results["screenshots"][f"{page}_{suffix}"] = {"height_px": h, "charts": s["charts"]}
                    print(f"captured {page}_{suffix}.png  height={h}px", flush=True)
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except Exception:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)
        shutil.rmtree(downloads, ignore_errors=True)
    (out / "capture_report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8503")
    ap.add_argument("--out", default="docs/screenshots")
    ap.add_argument("--edge", default=None)
    ap.add_argument("--port", type=int, default=9333)
    ap.add_argument("--only", nargs="*", help="capture only these page names")
    asyncio.run(run(ap.parse_args()))
