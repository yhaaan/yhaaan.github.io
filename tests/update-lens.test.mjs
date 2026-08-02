import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { parseKeywords, updateLensPayload } from "../scripts/update-lens.mjs";

const root = new URL("../", import.meta.url);

const loadPayload = async () =>
  JSON.parse(await readFile(new URL("data/lenses.json", root), "utf8"));

test("saves one lens without changing neighboring entries", async () => {
  const payload = await loadPayload();
  const before = structuredClone(payload.lenses[40]);
  const now = "2026-08-03T12:34:56.000Z";
  const updated = updateLensPayload(
    payload,
    {
      mode: "save",
      number: "42",
      title: "선택의 렌즈",
      content: "첫 문장\\n둘째 문장",
      keywords: " 선택, 피드백, 선택 ",
      notes: "공개 메모",
    },
    now,
  );

  assert.deepEqual(updated.lenses[40], before);
  assert.deepEqual(updated.lenses[41], {
    ...payload.lenses[41],
    title: "선택의 렌즈",
    content: "첫 문장\n둘째 문장",
    keywords: ["선택", "피드백"],
    notes: "공개 메모",
    favorite: false,
    updatedAt: now,
  });
  assert.equal(updated.exportedAt, now);
});

test("clears a lens while preserving its number", async () => {
  const payload = await loadPayload();
  payload.lenses[0] = {
    ...payload.lenses[0],
    title: "임시 제목",
    content: "임시 내용",
    keywords: ["임시"],
    notes: "임시 메모",
    favorite: true,
    updatedAt: "2026-08-03T00:00:00.000Z",
  };

  const updated = updateLensPayload(payload, { mode: "clear", number: 1 });
  assert.deepEqual(updated.lenses[0], {
    ...payload.lenses[0],
    title: "",
    content: "",
    keywords: [],
    notes: "",
    favorite: false,
    updatedAt: null,
  });
});

test("does not change timestamps when saved content is identical", async () => {
  const payload = await loadPayload();
  payload.exportedAt = "2026-08-03T00:00:00.000Z";
  payload.lenses[0] = {
    ...payload.lenses[0],
    title: "같은 제목",
    content: "같은 내용",
    keywords: ["같은", "키워드"],
    notes: "같은 메모",
    updatedAt: "2026-08-03T00:00:00.000Z",
  };

  const updated = updateLensPayload(
    payload,
    {
      mode: "save",
      number: 1,
      title: "같은 제목",
      content: "같은 내용",
      keywords: "같은, 키워드",
      notes: "같은 메모",
    },
    "2026-08-04T00:00:00.000Z",
  );

  assert.deepEqual(updated, payload);
});

test("rejects invalid numbers and empty save requests", async () => {
  const payload = await loadPayload();

  assert.throws(
    () => updateLensPayload(payload, { mode: "save", number: 114, title: "x" }),
    /1부터 113/,
  );
  assert.throws(
    () => updateLensPayload(payload, { mode: "save", number: "1e2", title: "x" }),
    /1부터 113/,
  );
  assert.throws(
    () => updateLensPayload(payload, { mode: "save", number: 1 }),
    /하나 이상/,
  );
});

test("normalizes comma-separated keywords", () => {
  assert.deepEqual(parseKeywords("게임,  선택\n게임,피드백"), [
    "게임",
    "선택",
    "피드백",
  ]);
});

test("keeps the editor owner-only and deploys the updated site", async () => {
  const [workflow, script] = await Promise.all([
    readFile(new URL(".github/workflows/update-lens.yml", root), "utf8"),
    readFile(new URL("scripts/update-lens.mjs", root), "utf8"),
  ]);

  assert.match(workflow, /workflow_dispatch:/);
  assert.match(workflow, /github.actor == github.repository_owner/);
  assert.match(workflow, /github.triggering_actor == github.repository_owner/);
  assert.match(workflow, /github.ref == 'refs\/heads\/main'/);
  assert.match(workflow, /contents:\s*write/);
  assert.match(workflow, /LENS_CONTENT:\s*\$\{\{ inputs\.content \}\}/);
  assert.match(workflow, /node scripts\/update-lens\.mjs/);
  assert.match(workflow, /git push origin HEAD:main/);
  assert.match(workflow, /actions\/deploy-pages@v4/);
  assert.doesNotMatch(script, /eval\(|exec\(|spawn\(/);
});
