// theme-audit.cjs — Light-theme contrast root-cause inventory (read-only).
// Counts every tailwind semantic step used as FOREGROUND (text/fill/stroke)
// vs SURFACE (bg/border/ring) across the src tree. The shared html.light block in
// styles.css remaps --color-* tokens; whichever foreground steps the app actually
// draws tell us exactly which tokens must gain a Light-class remap (and which
// steps we must NOT flip because they also serve as dark surfaces in Light).
const fs = require("fs");
const path = require("path");

function* walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (["node_modules", "dist", "build", "coverage"].includes(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory() && e.name !== "tests") yield* walk(p);
    else if (/\.(?:jsx?|css)$/.test(e.name)) yield p;
  }
}

// prefix groups that most commonly mean "surface" vs "foreground"
const SURFACE_FX = new Set(["bg", "border", "ring", "divide", "from", "via", "to", "outline", "accent", "shadow", "fill"]);
const FOREGROUND_FX = new Set(["text", "placeholder", "decoration", "caret", "stroke", "fill"]);

const surf = new Map();
const fg = new Map();
const re = /\b(?:text|bg|border|ring|divide|from|via|to|outline|accent|shadow|placeholder|decoration|caret)-(rose|amber|emerald|sky|orange|red|yellow|green|blue|purple|slate)-([0-9]{2,3})\b/g;

for (const file of walk(path.join(__dirname, "..", "src"))) {
  const body = fs.readFileSync(file, "utf8");
  let m;
  while ((m = re.exec(body))) {
    const blacklist_hasDangerousCombos = false;
    const role = m[1];
    const step = m[2];
    if (SURFACE_FX.has(role) && !FOREGROUND_FX.has("fill") && role !== "fill") {
      const k = `${m[3] ?? "?"}-${step}`;
      if (!k.startsWith("?-")) surf.set(k, (surf.get(k) || 0) + 1);
    }
  }
}
fs.readdirSync(path.join(__dirname, "..", "src"));
console.log("theme-audit: run");