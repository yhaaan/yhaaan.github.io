import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

test("exports the complete Korean lens library as static HTML", async () => {
  const html = await readFile(new URL("dist/client/index.html", root), "utf8");

  assert.match(html, /^<!doctype html>/i);
  assert.match(html, /<html[^>]*lang="ko"/i);
  assert.ok(
    html.includes("<title>렌즈 노트 — 개인 게임 디자인 서재</title>"),
  );
  assert.match(html, /name="robots" content="noindex, nofollow"/i);
  assert.ok(html.includes("렌즈 노트"));
  assert.ok(html.includes("113개의 렌즈를 나만의 언어로 기록"));

  const cards = html.match(/<article class="lens-card/g) ?? [];
  assert.equal(cards.length, 113);
});

test("keeps study data local and renders imported text safely", async () => {
  const source = await readFile(new URL("app/LensLibrary.tsx", root), "utf8");

  assert.match(source, /localStorage/);
  assert.match(source, /jesse-lenses:data:v1/);
  assert.match(source, /JSON\.stringify/);
  assert.match(source, /JSON\.parse/);
  assert.doesNotMatch(source, /dangerouslySetInnerHTML/);
});

test("includes a repository-aware GitHub Pages deployment", async () => {
  const [config, viteConfig, workflow] = await Promise.all([
    readFile(new URL("next.config.ts", root), "utf8"),
    readFile(new URL("vite.config.ts", root), "utf8"),
    readFile(new URL(".github/workflows/deploy-pages.yml", root), "utf8"),
  ]);

  assert.match(config, /output:\s*"export"/);
  assert.match(config, /trailingSlash:\s*true/);
  assert.match(viteConfig, /GITHUB_REPOSITORY/);
  assert.match(viteConfig, /githubPagesAssetBase/);
  assert.match(workflow, /actions\/deploy-pages@v4/);
  assert.match(workflow, /path:\s*\.\/dist\/client/);
});
