// theme-inventory.cjs — Light-theme token audit (read-only).
// Walks ../src, counting Tailwind semantic color-step utilities by role:
//   text:  foreground accents (text-, placeholder-, decoration-, caret-, fill-, stroke-)
//   bg:    surface accents (bg-, from-, to-, via-, ring-, outline-, accent-, shadow-)
//   line:  border accents (border-, divide-, ring-)
// Prints a table sorted by color then step so we can see exactly which semantic
// steps the shared html.light remap in styles.css must darken for Light mode
// without touching any Dark-mode rendering or per-page CSS.
const fs = require("fs");
const path = require("path");

function* walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (["node_modules", "dist", "build", "coverage"].includes(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory() && e.name !== "tests") yield* walk(p);
    else if (/\.(jsx?|css)$/.test(e.name)) yield p;
  }
}

// (role) -> (color-step) -> count
const text = new Map();
const fill = new Map();
const line = new Map();
const roleRegex =
  /\b(text|placeholder|decoration|caret|fill|stroke|bg|from|to|via|ring|outline|accent|shadow|bg-gradient)-(rose|amber|emerald|sky)-(50|100|200|300|400|500|600|700|800|900|950)\b/g;

for (const file of walk(path.join(__dirname, "..", "src"))) {
  const body = fs.readFileSync(file, "utf8");
  let m;
  roleRegex.lastIndex = 0;
  while ((m = roleRegex.exec(body))) {
    const role = m[1];
    const key = `${m[2]}-${m[3]}`;
    const fgRole = ["text", "placeholder", "decoration", "caret", "fill", "stroke"].includes(role);
    const bgRole = ["bg", "from", "to", "via", "ring", "outline", "accent", "shadow"].includes(role);
    const ln = role === "border" || role === "divide";
    const bucket = fgRole ? text : bgRole ? fill : ln ? line : text;
    bucket.set(key, (bucket.get(key) || 0) + 1);
  }
}

const colorOrder = { rose: 0, amber: 1, emerald: 2, sky: 3 };
const stepOrder = {
  "50": 0, "100": 1, "200": 2, "300": 3, "400": 4, "500": 5,
  "600": 6, "700": 7, "800": 8, "900": 9, "950": 10,
};

const all = new Set([...text.keys(), ...fill.keys(), ...line.keys()]);
const rows = [...all].sort((a, b) => {
  const [ca, sa] = a.split("-");
  const [cb, sb] = b.split("-");
  return colorOrder[ca] - colorOrder[cb] || stepOrder[sa] - stepOrder[sb];
});

console.log("Semantic accent steps used across the frontend (fg vs bg vs border):");
for (const key of rows) {
  const t = text.get(key) || 0;
  const f = fill.get(key) || 0;
  const l = line.get(key) || 0;
  const flag = t > 0 && f > 0 ? " <-- fg AND bg (remap is ambiguous)" : "";
  console.log(`${key.padEnd(8)}  fg:${String(t).padStart(3)}  bg:${String(f).padStart(3)}  line:${String(l).padStart(3)}${flag}`);
}
