export const TOTAL_LENSES = 100;

export type LensCard = {
  number: number;
  title: string;
  content: string;
  keywords: string[];
  notes: string;
  updatedAt: string | null;
};

const APP_ID = "art-of-game-design-lens-notes";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const cleanLens = (value: unknown): LensCard => {
  if (!isRecord(value)) {
    throw new Error("Each lens in data/lenses.json must be an object.");
  }

  const number = value.number;
  const content = value.content ?? value.body;
  const notes = value.notes ?? value.memo ?? "";
  const updatedAt = value.updatedAt ?? null;

  if (
    !Number.isInteger(number) ||
    (number as number) < 1 ||
    (number as number) > TOTAL_LENSES
  ) {
    throw new Error(`Lens number must be an integer from 1 to ${TOTAL_LENSES}.`);
  }

  if (
    typeof value.title !== "string" ||
    typeof content !== "string" ||
    typeof notes !== "string" ||
    !Array.isArray(value.keywords) ||
    !value.keywords.every((keyword) => typeof keyword === "string") ||
    !(updatedAt === null || typeof updatedAt === "string")
  ) {
    throw new Error(`Lens ${number} has an invalid field type.`);
  }

  return {
    number: number as number,
    title: value.title,
    content,
    keywords: [
      ...new Set(
        value.keywords
          .map((keyword) => keyword.trim())
          .filter(Boolean),
      ),
    ],
    notes,
    updatedAt,
  };
};

export function loadPublishedLenses(value: unknown): LensCard[] {
  if (
    !isRecord(value) ||
    value.appId !== APP_ID ||
    value.schemaVersion !== 1 ||
    value.edition !== 2 ||
    value.language !== "ko" ||
    !Array.isArray(value.lenses)
  ) {
    throw new Error("data/lenses.json does not use the supported lens schema.");
  }

  if (value.lenses.length !== TOTAL_LENSES) {
    throw new Error(`data/lenses.json must contain exactly ${TOTAL_LENSES} lenses.`);
  }

  const lenses = value.lenses.map(cleanLens);
  const numbers = new Set(lenses.map((lens) => lens.number));

  if (numbers.size !== TOTAL_LENSES) {
    throw new Error("Lens numbers in data/lenses.json must be unique.");
  }

  for (let number = 1; number <= TOTAL_LENSES; number += 1) {
    if (!numbers.has(number)) {
      throw new Error(`Lens ${number} is missing from data/lenses.json.`);
    }
  }

  return lenses.sort((left, right) => left.number - right.number);
}
