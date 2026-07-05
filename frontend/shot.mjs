import { chromium } from "playwright";

const OUT = "./.shots";
const url = "http://localhost:3000/";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(url, { waitUntil: "networkidle" });
await page.waitForTimeout(500);

// find the growth-story section (the #how wrapper) top offset
const howTop = await page.evaluate(() => {
  const el = document.querySelector("#how");
  return el ? el.getBoundingClientRect().top + window.scrollY : 0;
});
const sectionH = await page.evaluate(() => {
  const el = document.querySelector("#how section");
  return el ? el.offsetHeight : 0;
});

// capture at fractions through the pinned scroll
const fracs = [0.02, 0.25, 0.5, 0.75, 0.95];
for (let i = 0; i < fracs.length; i++) {
  const y = howTop + sectionH * fracs[i];
  await page.evaluate((yy) => window.scrollTo(0, yy), y);
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${OUT}/growth-${i}.png` });
}

// also a top-of-page shot
await page.evaluate(() => window.scrollTo(0, 0));
await page.waitForTimeout(400);
await page.screenshot({ path: `${OUT}/top.png` });

await browser.close();
console.log("done");
