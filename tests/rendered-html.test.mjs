import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

test("exports the complete public Korean lens library as static HTML", async () => {
  const html = await readFile(new URL("dist/client/index.html", root), "utf8");

  assert.match(html, /^<!doctype html>/i);
  assert.match(html, /<html[^>]*lang="ko"/i);
  assert.ok(
    html.includes("<title>렌즈 노트 — 게임 디자인 렌즈 컬렉션</title>"),
  );
  assert.match(html, /name="robots" content="index, follow"/i);
  assert.ok(html.includes("공개 읽기 전용"));
  assert.ok(html.includes("모든 방문자에게 같은 내용이 표시됩니다"));

  const cards = html.match(/<article class="lens-card/g) ?? [];
  assert.equal(cards.length, 113);
});

test("uses a valid repository-backed data file and exposes no visitor editing path", async () => {
  const [source, pageSource, json] = await Promise.all([
    readFile(new URL("app/LensLibrary.tsx", root), "utf8"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("data/lenses.json", root), "utf8"),
  ]);
  const payload = JSON.parse(json);

  assert.equal(payload.appId, "art-of-game-design-lens-notes");
  assert.equal(payload.schemaVersion, 1);
  assert.equal(payload.edition, 2);
  assert.equal(payload.language, "ko");
  assert.equal(payload.lenses.length, 113);
  assert.deepEqual(
    payload.lenses.map((lens) => lens.number),
    Array.from({ length: 113 }, (_, index) => index + 1),
  );
  assert.ok(
    payload.lenses.every(
      (lens) =>
        typeof lens.title === "string" &&
        typeof lens.content === "string" &&
        Array.isArray(lens.keywords) &&
        lens.keywords.every((keyword) => typeof keyword === "string") &&
        typeof lens.notes === "string",
    ),
  );

  assert.match(pageSource, /data\/lenses\.json/);
  assert.doesNotMatch(source, /localStorage|sessionStorage|FileReader|new Blob|createObjectURL/);
  assert.doesNotMatch(source, /type=["']file["']|<form|contentEditable/);
  assert.doesNotMatch(source, /dangerouslySetInnerHTML/);
});

test("includes a repository-aware and verified GitHub Pages deployment", async () => {
  const [config, viteConfig, workflow] = await Promise.all([
    readFile(new URL("next.config.ts", root), "utf8"),
    readFile(new URL("vite.config.ts", root), "utf8"),
    readFile(new URL(".github/workflows/deploy-pages.yml", root), "utf8"),
  ]);

  assert.match(config, /output:\s*"export"/);
  assert.match(config, /trailingSlash:\s*true/);
  assert.match(viteConfig, /GITHUB_REPOSITORY/);
  assert.match(viteConfig, /githubPagesAssetBase/);
  assert.match(workflow, /node --test tests\/rendered-html\.test\.mjs/);
  assert.match(workflow, /actions\/deploy-pages@v4/);
  assert.match(workflow, /path:\s*\.\/dist\/client/);
});
