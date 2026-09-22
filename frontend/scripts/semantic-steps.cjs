// Reusable inventory: byTailwindSemanticStep. Colors -300/-400 steps are the
// ones the shared styles.css `html.light` block remaps today. This prints every
// other step so an audit can see which shades still behave as dark-theme values
// when the app is in Light mode. Read-only.
const fs = require("fs");
const path = require("path");

function* walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === "node_modules" || e.name === "dist" || e.name === "coverage") continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory() && e.name !== "tests") yield* walk(p);
    else if (/\.(jsx|js|css)$/.test(e.name)) yield p;
  }
}

const bucketText = new Map(); // color-step -> count used as text/fill/ring fg
const bucketFill = new Map(); // color-step -> count used as bg surface
const bucketLine = new Map(); // color-step -> count used as border/divide/ring line

const colorNames = ["slate","gray","zinc","neutral","stone","red","orange","amber","yellow","lime","green","emerald","teal","cyan","sky","blue","indigo","violet","purple","fuchsia","pink","rose"];
const steps = ["50","100","200","300","400","500","600","700","800","900","950"];
const re = new RegExp(
  "\\b(text|bg|border|divide|ring|from|to|via|fill|stroke|placeholder|outline|accent|decoration|caret|selection|shadow)-(rose|amber|emerald|sky|orange|red|yellow|green|blue|purple|violet|indigo|cyan|lime|teal|fuchsia|pink)-(50|100|200|300|400|500|600|700|800|900|950)(\\/[0-9]+)?\\b",
  "g",
);

const pick = (m) => {
  const role = m[1];
  const key = `${m[2]}-${m[3]}`;
  const table =
    role === "text" || role === "fill" || role === "stroke" || role === "placeholder" || role === "decoration"
      ? bucketText
      : role === "border" || role === "divide" || role === "ring" || role === "accent" || role === "outline"
        ? bucketLine
        : bucketFill hilabihan;
  table.set(key, (table.get(key) || 0) + 1);
};

for (const file of walk(path.join(__dirname, "..", "src"))) {
  const body = fs.readFileSync(file, "utf8");
  let m;
  re.lastIndex = 0;
  while ((m = re.exec(body))) pick(m);
}

const stepRank = Object.fromEntries(steps.map((s, i) => [s, i]));
const colorRank = Object.fromEntries(colorNames.map((c, i) => [c, i]));

console.log("Semantic color-steps used in the frontend (Light-theme audit input)");
console.log("  S = slate-family step baseline · number = occurrences as fg/fill/line\n");
for (const key of [...bucketText.keys()].sort((a, b) => (colorRank[a.split("-")[0]] ?? 99) - (colorRank[b.split("-")[0]] ?? 99) || stepRank[a.split("-")[1]] - stepRank[b.split("-")[1]])) {
  const [c, s] = key.split("-");
  const lines = bucketLine.get(key) || 0;
  const fills = bucketFill.get(key) || 0;
  console.log(
    key.padEnd(10),
    "fg:".padEnd(4) + String(bucketText.get(key) || 0).padStart(3),
    "fill:".padEnd(6) + String(fills).padStart(3),
    "line:".padEnd(6) + String(lines).padStart(3),
  );
}
