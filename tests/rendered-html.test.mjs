import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

test("exports the complete Korean lens library as static HTML", async () => {
  const html = await readFile(new URL("dist/client/index.html", root), "utf8");

  assert.match(html, /^<!doctype html>/i);
  assert.match(html, /<html[^>]*lang="ko"/i);
  assert.match(html, /name="robots" content="index, follow"/i);
  assert.ok(html.includes("공개 기본값에서 자유롭게 편집할 수 있습니다."));
  assert.ok(html.includes("운영자의 기본값 위에 나만의 수정본이"));

  const cards = html.match(/<article class="lens-card/g) ?? [];
  assert.equal(cards.length, 113);
});

test("uses repository defaults and provides browser-local editing", async () => {
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
  assert.ok(
    payload.lenses
      .filter((lens) => lens.content.trim())
      .every((lens) => lens.content.startsWith("#### ")),
  );
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
  assert.match(source, /localStorage/);
  assert.match(source, /jesse-lenses:visitor-data:v2/);
  assert.match(source, /<form/);
  assert.match(source, /type="file"/);
  assert.match(source, /new Blob/);
  assert.match(source, /createObjectURL/);
  assert.match(source, /restoreDefaults/);
  assert.match(source, /const openViewer/);
  assert.match(source, /const moveViewer/);
  assert.match(source, /ArrowLeft/);
  assert.match(source, /ArrowRight/);
  assert.match(source, /ReactMarkdown/);
  assert.match(source, /remarkGfm/);
  assert.match(source, /skipHtml/);
  assert.match(source, /markdownPreviewComponents/);
  assert.match(source, /components=\{markdownPreviewComponents\}/);
  assert.match(source, /className="card-preview-link"/);
  assert.match(source, /openEditor\(viewerNumber, null, true\)/);
  assert.doesNotMatch(source, /dangerouslySetInnerHTML/);
  assert.doesNotMatch(source, /<h3>내용<\/h3>/);
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
  assert.match(workflow, /run:\s*npm run test:unit/);
  assert.match(workflow, /actions\/deploy-pages@v4/);
  assert.match(workflow, /path:\s*\.\/dist\/client/);
});
test("keeps Markdown list markers visible after the global CSS reset", async () => {
  const css = await readFile(new URL("app/globals.css", root), "utf8");

  assert.ok(css.includes(".markdown-body ul {"));
  assert.ok(css.includes("list-style: disc outside;"));
  assert.ok(css.includes(".markdown-body ol {"));
  assert.ok(css.includes("list-style: decimal outside;"));
  assert.ok(css.includes(".markdown-body .contains-task-list"));
});