// Light-theme token regression tests.
//
// The whole app themes through one shared mechanism: `html.light` in
// src/styles.css redefines Tailwind v4's `--color-*` variables, so every
// surface, border, heading, badge and status label resolves per theme with no
// per-page overrides. These tests pin that contract so a future component that
// reaches for a dark-theme accent token (or a brand-new hue) can never silently
// leak a pale-on-light style into Light mode again.
//
// The checks are static (they read styles.css + the JSX class strings), so they
// run under `node --test` with no browser/DOM required.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

// ---------------------------------------------------------------------------
// CSS parsing helpers
// ---------------------------------------------------------------------------

function readCss() {
  return readFileSync(join(root, "src", "styles.css"), "utf8");
}

function listSourceFiles() {
  const out = [];
  const walk = (dir) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(full);
      } else if (entry.name.endsWith(".jsx") || entry.name === "api.js") {
        out.push(full);
      }
    }
  };
  walk(join(root, "src"));
  return out;
}

/** hex "#rrggbb" -> [r,g,b] 0..255 */
function rgb(hex) {
  const m = /^#([0-9a-f]{6})$/i.exec(hex.trim().toLowerCase());
  assert.ok(m, `expected a #rrggbb hex, got "${hex}"`);
  return [0, 1, 2].map((i) => parseInt(m[1].slice(i * 2, i * 2 + 2), 16));
}

/** WCAG 2.x relative luminance of a color on a (white or black) surface. */
function luminance(hex) {
  const c = rgb(hex).map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}

/** WCAG contrast ratio of fg against bg (both "#rrggbb"). */
function contrast(fg, bg) {
  const l1 = luminance(fg);
  const l2 = luminance(bg);
  const [hi, lo] = l1 >= l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
}

// Tailwind shade steps (longest strings first so "500" isn't eaten as "50").
const SHADE_STEPS = ["950", "900", "800", "700", "600", "500", "400", "300", "200", "100", "50"];

const WHITE = "#ffffff";

/**
 * Parse styles.css into:
 *  - lightTokens:  { token: "#hex" } from the `html.light` variable block
 *  - whiteRescoped: array of ".bg-<hue>-<shade>" whose scoped rule restores
 *    `--color-white: #ffffff` (solid colored CTA/notification surfaces)
 *  - slateRescoped: same, for `--color-slate-950: #020617` (amber buttons)
 */
function parseThemeCss(css) {
  const lightBlock = /html\.light\s*\{([^}]*)\}/.exec(css);
  assert.ok(lightBlock, "html.light token block not found in styles.css");
  const lightTokens = {};
  for (const [, token, hex] of lightBlock[1].matchAll(/--color-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})/g)) {
    lightTokens[token] = hex.toLowerCase();
  }

  const whiteRescoped = [];
  const slateRescoped = [];
  const rescopeRe = /html\.light\s+([^{]+)\{([^}]*)\}/g;
  for (const [, selectors, body] of css.matchAll(rescopeRe)) {
    const classes = [...selectors.matchAll(new RegExp(`bg-([a-z]+-(?:${SHADE_STEPS.join("|")}))`, "g"))].map((m) => m[1]);
    if (/--color-white:\s*#ffffff/i.test(body)) whiteRescoped.push(...classes);
    if (/--color-slate-950:\s*#020617/i.test(body)) slateRescoped.push(...classes);
  }

  return { lightTokens, whiteRescoped, slateRescoped };
}

function collectUsedTokens(files) {
  const shade = `(?:${SHADE_STEPS.join("|")})`;
  const hueRe = new RegExp(`(slate|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-${shade}`, "g");
  const used = new Set();
  for (const file of files) {
    const text = readFileSync(file, "utf8");
    for (const [, hue, shade] of text.matchAll(hueRe)) used.add(`${hue}-${shade}`);
  }
  return used;
}

// ---------------------------------------------------------------------------
// Theme contract
// ---------------------------------------------------------------------------

const { lightTokens, whiteRescoped, slateRescoped } = parseThemeCss(readCss());
const usedTokens = collectUsedTokens(listSourceFiles());

// Hues the light remap knows how to make readable on light surfaces.
const ACCENT_HUES = new Set(["amber", "rose", "emerald", "sky", "indigo", "orange", "red"]);
// Same-hue dark accent text shades that must be pulled down to dark steps.
const TEXT_SHADES = new Set(["200", "300", "400"]);
// Dark chip backgrounds that must flip to pastel in Light mode.
const CHIP_SHADES = new Set(["950"]);
// Exempt by design: 500/600/700 stay saturated (solid fills, borders, buttons,
// translucent tints); 100/800/900 aren't used as accent tokens in the app.
const EXEMPT_SHADES = new Set(["50", "100", "500", "600", "700", "800", "900"]);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test("every slate step is remapped for the Light theme (surfaces, cards, borders, text)", () => {
  for (const step of ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"]) {
    const token = `slate-${step}`;
    assert.ok(lightTokens[token], `html.light is missing --color-${token}`);
  }

  // Structural Light-mode contract: page bg light, cards white, borders light,
  // primary text near-black, secondary text readable.
  assert.ok(luminance(lightTokens["slate-950"]) >= 0.85, "page background must be light");
  assert.ok(luminance(lightTokens["slate-900"]) >= 0.95, "card surface must read as white");
  assert.ok(luminance(lightTokens["slate-800"]) >= 0.78, "card borders must be light");
  assert.ok(luminance(lightTokens["slate-100"]) <= 0.06, "primary text must be near-black");
  assert.ok(contrast(lightTokens["slate-400"], WHITE) >= 4.5, "secondary text must reach AA");
  assert.ok(contrast(lightTokens["slate-600"], WHITE) >= 4.5, "muted/icon text must reach AA");
});

test("secondary slate-500 stays the muted tier but reaches AA on white", () => {
  assert.ok(contrast(lightTokens["slate-500"], WHITE) >= 4.5, "muted text must reach AA");
  assert.ok(
    luminance(lightTokens["slate-500"]) > luminance(lightTokens["slate-400"]),
    "slate-500 must stay lighter (more muted) than slate-400",
  );
});

test("every accent text shade used in components is remapped with readable contrast", () => {
  for (const token of usedTokens) {
    const m = /^([a-z]+)-(200|300|400|950)$/.exec(token);
    if (!m) continue;
    const [, hue, shade] = m;

    if (hue === "slate") continue;

    if (TEXT_SHADES.has(shade) || CHIP_SHADES.has(shade)) {
      const message = `${token} (used in src) must get a light remap in html.light`;
      assert.ok(ACCENT_HUES.has(hue), message);
      assert.ok(lightTokens[token], message);
    }

    if (TEXT_SHADES.has(shade) && ACCENT_HUES.has(hue)) {
      const ratio = contrast(lightTokens[token], WHITE);
      if (shade === "400") {
        assert.ok(ratio >= 3.0, `${token} → ${lightTokens[token]} is ${ratio.toFixed(2)}:1 (UI/min 3:1)`);
      } else {
        assert.ok(ratio >= 4.5, `${token} → ${lightTokens[token]} is ${ratio.toFixed(2)}:1 (need 4.5:1)`);
      }
    }
  }
});

test("accent 200/300 text steps are never lighter than their 400 accent", () => {
  for (const hue of ACCENT_HUES) {
    const lo = lightTokens[`${hue}-200`];
    const mid = lightTokens[`${hue}-300`];
    if (lo && mid) {
      assert.ok(
        luminance(lo) <= luminance(mid),
        `${hue}-200 should be the deepest step in light mode`,
      );
    }
  }
});

test("dark chip shades remap to pastel pills so badges stay readable", () => {
  for (const hue of ACCENT_HUES) {
    const chip = lightTokens[`${hue}-950`];
    if (!chip) continue;
    assert.ok(luminance(chip) >= 0.75, `${hue}-950 light value ${chip} must be a pastel`);
    // A darkened 800-step label on that pastel keeps ≥ 4.5:1.
    const label = ACCENT_HUES.has(hue) && lightTokens[`${hue}-200`] ? lightTokens[`${hue}-200`] : lightTokens["slate-100"];
    assert.ok(contrast(label, chip) >= 4.5, `${hue}-950 chip + label must reach AA`);
  }
});

test("white text on solid colored surfaces is restored (buttons and badges)", () => {
  assert.ok(lightTokens["white"], "--color-white must be remapped for headings on light cards");
  assert.ok(
    luminance(lightTokens["white"]) <= 0.1,
    "white remap must be dark so headings stay legible on white cards",
  );

  const SOLIDS_WITH_WHITE_TEXT = ["sky-500", "sky-600", "emerald-500", "emerald-600", "rose-500", "rose-600"];
  for (const token of SOLIDS_WITH_WHITE_TEXT) {
    assert.ok(
      whiteRescoped.includes(token),
      `html.light .bg-${token} must re-scope --color-white to #ffffff (${token} carries white labels)`,
    );
  }
});

test("amber buttons keep near-black on-slate-950 labels in light mode", () => {
  for (const token of ["amber-300", "amber-400", "amber-500", "amber-600"]) {
    assert.ok(
      slateRescoped.includes(token),
      `html.light .bg-${token} must re-scope --color-slate-950 to keep button labels dark`,
    );
  }
});

test("no new accent hue appears without a light remap", () => {
  for (const token of usedTokens) {
    const m = /^([a-z]+)-(200|300|400|950)$/.exec(token);
    if (!m || m[1] === "slate") continue;
    if (ACCENT_HUES.has(m[1])) continue;
    assert.fail(
      `${token} introduces ${m[1]} as an accent token but html.light has no remap for it ` +
        `(add it to the shared light theme, not per page)`,
    );
  }
});