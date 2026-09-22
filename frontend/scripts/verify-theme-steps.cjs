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

const SURF = new Set(["bg", "from", "via", "to", "ring", "outline", "accent", "border", "divide"]);
const FG = new Set(["text", "placeholder", "decoration", "caret", "stroke", "fill"]);

const stepRe = new RegExp(
  "\\b(" + [...FG].join("|") + "|" + [...SURF].join("|") + ")-(rose|amber|emerald|sky|orange|red|green|blue|purple|slate)-([0-9]{2,3})\\b",
  "g",
);

const fgCount = new Map();
const surfCount = new Map();

for (const file of walk(path.join(__dirname, "..", "src"))) {
  const body = fs.readFileSync(file, "utf8");
  let m;
  stepRe.lastIndex = 0;
  while ((m = stepRe.exec(body))) {
    const key = m[2] + "-" + m[3];
    if (FG.has(m[1])) fgCount.set(key, (fgCount.get(key) || 0) + 1);
    if (SURF.has(m[1])) surfCount.set(key, (surfCount.get(key) || 0) + 1);
  }
}

const colorOrder = ["rose", "amber", "emerald", "sky", "orange", "red", "green", "blue", "purple", "slate"];
const stepOrder = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"];

const keys = new Set([...fgCount.keys(), ...surfCount.keys()]);
console.log("semantic bg/border surface steps   (counts of bg-/from-/ring-... usages per color-step)");
for (const k of [...keys].sort()) {
  const n = surfCount.get(k) || 0;
  if (n > 0) console.log(`  ${k.padEnd(10)} ${String(n).padStart(3)}`);
}
console.log("semantic foregmed text steps   (counts of text-/placeholder-... usages per color-step)");
for (const k of [...keys].sort()) {
  const n = fgCount.get(k) || 0;
  if (n > 0) console.log(`  ${k.padEnd(10)} ${String(n).padStart(3)}`);
}
