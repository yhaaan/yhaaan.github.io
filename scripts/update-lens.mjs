import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TOTAL_LENSES = 100;
const APP_ID = "art-of-game-design-lens-notes";
const VALID_MODES = new Set(["save", "clear"]);

const limits = {
  title: 200,
  content: 10_000,
  notes: 5_000,
  keywordText: 4_000,
  keywords: 100,
  keyword: 100,
};

const isRecord = (value) =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const cleanText = (value, field, limit) => {
  const text = String(value ?? "")
    .replace(/\r\n?/g, "\n")
    .replace(/\\n/g, "\n")
    .trim();

  if (text.includes("\0")) {
    throw new Error(`${field}에는 null 문자를 사용할 수 없습니다.`);
  }
  if (text.length > limit) {
    throw new Error(`${field}은(는) ${limit.toLocaleString("ko-KR")}자를 넘을 수 없습니다.`);
  }

  return text;
};

export const parseKeywords = (value) => {
  const keywordText = String(value ?? "");
  if (keywordText.length > limits.keywordText) {
    throw new Error("키워드 입력은 4,000자를 넘을 수 없습니다.");
  }

  const keywords = keywordText
    .split(/[,\n]/u)
    .map((keyword) => keyword.normalize("NFKC").trim())
    .filter(Boolean);
  const unique = [...new Set(keywords)];

  if (unique.length > limits.keywords) {
    throw new Error(`키워드는 최대 ${limits.keywords}개까지 입력할 수 있습니다.`);
  }
  if (unique.some((keyword) => keyword.length > limits.keyword)) {
    throw new Error(`키워드 하나는 ${limits.keyword}자를 넘을 수 없습니다.`);
  }

  return unique;
};

const validatePayload = (payload) => {
  if (
    !isRecord(payload) ||
    payload.appId !== APP_ID ||
    payload.schemaVersion !== 1 ||
    payload.edition !== 2 ||
    payload.language !== "ko" ||
    !Array.isArray(payload.lenses) ||
    payload.lenses.length !== TOTAL_LENSES ||
    !(payload.exportedAt === null || typeof payload.exportedAt === "string")
  ) {
    throw new Error("data/lenses.json의 형식이 올바르지 않습니다.");
  }

  const numbers = new Set();
  for (const lens of payload.lenses) {
    if (
      !isRecord(lens) ||
      !Number.isInteger(lens.number) ||
      lens.number < 1 ||
      lens.number > TOTAL_LENSES ||
      numbers.has(lens.number) ||
      typeof lens.title !== "string" ||
      typeof lens.content !== "string" ||
      !Array.isArray(lens.keywords) ||
      !lens.keywords.every((keyword) => typeof keyword === "string") ||
      typeof lens.notes !== "string" ||
      typeof lens.favorite !== "boolean" ||
      !(lens.updatedAt === null || typeof lens.updatedAt === "string")
    ) {
      throw new Error("렌즈 번호는 1~100 범위에서 중복 없이 존재해야 합니다.");
    }
    numbers.add(lens.number);
  }

  for (let number = 1; number <= TOTAL_LENSES; number += 1) {
    if (!numbers.has(number)) {
      throw new Error("렌즈 " + number + "번이 누락되었습니다.");
    }
  }
};

export function updateLensPayload(payload, input, now = new Date().toISOString()) {
  validatePayload(payload);

  const mode = String(input.mode ?? "save");
  const numberText = String(input.number ?? "").trim();
  const number = Number(numberText);

  if (!VALID_MODES.has(mode)) {
    throw new Error("작업 방식은 save 또는 clear여야 합니다.");
  }
  if (!/^(?:[1-9]|[1-9][0-9]|100)$/.test(numberText)) {
    throw new Error("렌즈 번호는 1부터 100 사이의 정수여야 합니다.");
  }

  const nextPayload = structuredClone(payload);
  const lensIndex = nextPayload.lenses.findIndex((lens) => lens.number === number);
  if (lensIndex < 0) {
    throw new Error(`${number}번 렌즈를 찾을 수 없습니다.`);
  }

  const current = nextPayload.lenses[lensIndex];

  let replacement;

  if (mode === "clear") {
    replacement = {
      title: "",
      content: "",
      keywords: [],
      notes: "",
      favorite: false,
      updatedAt: null,
    };
  } else {
    const title = cleanText(input.title, "제목", limits.title);
    const content = cleanText(input.content, "내용", limits.content);
    const notes = cleanText(input.notes, "보충 메모", limits.notes);
    const keywords = parseKeywords(input.keywords);

    if (!title && !content && !notes && keywords.length === 0) {
      throw new Error("save 작업에는 제목, 내용, 키워드, 보충 메모 중 하나 이상이 필요합니다.");
    }

    replacement = {
      title,
      content,
      keywords,
      notes,
      favorite: false,
      updatedAt: now,
    };
  }

  const contentChanged =
    current.title !== replacement.title ||
    current.content !== replacement.content ||
    JSON.stringify(current.keywords) !== JSON.stringify(replacement.keywords) ||
    current.notes !== replacement.notes ||
    current.favorite !== replacement.favorite ||
    (mode === "clear" && current.updatedAt !== null);

  if (!contentChanged) return nextPayload;

  nextPayload.lenses[lensIndex] = { ...current, ...replacement };
  nextPayload.lenses.sort((left, right) => left.number - right.number);
  nextPayload.exportedAt = now;
  validatePayload(nextPayload);
  return nextPayload;
}

const projectRoot = fileURLToPath(new URL("../", import.meta.url));

async function main() {
  const dataPath = process.env.LENS_DATA_FILE
    ? path.resolve(process.env.LENS_DATA_FILE)
    : path.join(projectRoot, "data", "lenses.json");
  const payload = JSON.parse(await readFile(dataPath, "utf8"));
  const updated = updateLensPayload(payload, {
    mode: process.env.LENS_MODE,
    number: process.env.LENS_NUMBER,
    title: process.env.LENS_TITLE,
    content: process.env.LENS_CONTENT,
    keywords: process.env.LENS_KEYWORDS,
    notes: process.env.LENS_NOTES,
  });

  await writeFile(dataPath, `${JSON.stringify(updated, null, 2)}\n`, "utf8");
  const verb = process.env.LENS_MODE === "clear" ? "비웠습니다" : "저장했습니다";
  console.log(`렌즈 #${process.env.LENS_NUMBER}을(를) ${verb}.`);
}

const isMain =
  process.argv[1] &&
  path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));

if (isMain) {
  main().catch((error) => {
    console.error(`렌즈 저장 실패: ${error.message}`);
    process.exitCode = 1;
  });
}
