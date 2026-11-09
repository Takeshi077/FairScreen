import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "../..");
const SCREENSHOT_DIR = path.join(REPO_ROOT, "docs", "screenshots");
const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:3000";

const PAGES = [
  { name: "overview", path: "/" },
  { name: "gaps", path: "/gaps" },
  { name: "before-after", path: "/before-after" },
  { name: "models", path: "/models" },
  { name: "shortlist", path: "/shortlist" },
  { name: "accuracy", path: "/accuracy" },
  { name: "runs", path: "/runs" },
  { name: "method", path: "/method" },
];

const VIEWPORTS = [
  { name: "desktop", width: 1280, height: 800 },
  { name: "phone", width: 375, height: 667, isMobile: true },
];

async function main() {
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }

  console.log(`Launching Chromium to capture screenshots of ${BASE_URL}...`);
  const browser = await chromium.launch();

  try {
    for (const vp of VIEWPORTS) {
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        isMobile: Boolean(vp.isMobile),
      });
      const page = await context.newPage();

      for (const p of PAGES) {
        const url = `${BASE_URL}${p.path}`;
        const filename = `${p.name}-${vp.name}.png`;
        const filepath = path.join(SCREENSHOT_DIR, filename);

        console.log(`Capturing ${filename} from ${url}...`);
        try {
          await page.goto(url, { waitUntil: "networkidle", timeout: 15000 });
          // Wait a moment for any chart animations or dynamic fonts to settle
          await page.waitForTimeout(600);
          await page.screenshot({ path: filepath, fullPage: true });
          console.log(`✓ Saved ${filename}`);
        } catch (err) {
          console.warn(`! Could not capture ${filename} from ${url}: ${err.message}`);
        }
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }
  console.log("Screenshot capture complete.");
}

main().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});

