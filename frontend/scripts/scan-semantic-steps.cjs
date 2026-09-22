const fs = require("fs");
const path = require("path");

function* walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name === "node_modules" || e.name === "dist" || e.name === "tests") continue;
      yield* walk(p);
    } else if (/\.(jsx|js|css)$/.test(e.name)) {
      yield p;
    }
  }
}

const txt = {}; // text-<c>-<s>
const bgs = {}; // bg / border / ring / from / to / via fills
const re = /(text|bg|border|ring|from|to|via|divide|placeholder|outline|accent|fill|stroke)-(rose|amber|emerald|sky|orange|violet|indigo|cyan|lime|teal|fuchsia|pink|red|yellow|green|blue|purple)-(\d{3})(?:\/[0-9.]+)?/g;
const start = path.join(__dirname, "..", "src");

for (const file of walk(start)) {
  const code = fs.readFileSync(file, "utf8");
  let m;
  re.lastIndex = 0;
  while ((m = re.exec(code))) {
    const kind = m[1];
    const key = `${m[2]}-${m[3]}`;
    const bucket = kind === "text" ? txt : bgs;
    bucket[key] = (bucket[key] || 0) + 1;
  }
}

const all = new Set([...Object.keys(txt), ...Object.keys(bgs)]);
const colorOrder = ["rose", "amber", "emerald", "sky", "orange", "violet", "indigo", "cyan", "lime", "teal", "fuchsia", "pink", "red", "yellow", "green", "blue", "purple"];

console.log("=== semantic steps -> [text][bg/fill] counts ===");
for (const c of colorOrder) {
  for (const s of [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]) {
    const k = `${c}-${s}`;
    if (!all.has(k)) continue;
    const t = txt[k] || 0;
    const b = bgs[k] || 0;
    const flag = t > 0 && b > 0 ? "  <-- BOTH" : "";
    console.log(`${k.padEnd(14)} text:${String(t).padStart(3)}  fill:${String(b).padStart(3)}${flag}`);
  }
}
