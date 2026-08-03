"use client";

import {
  ChangeEvent,
  FormEvent,
  KeyboardEvent as ReactKeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

const TOTAL_LENSES = 113;
const STORAGE_KEY = "jesse-lenses:visitor-data:v2";
const BACKUP_DATE_KEY = "jesse-lenses:last-backup:v1";
const IMPORT_BACKUP_KEY = "jesse-lenses:pre-import:v1";
const MAX_IMPORT_BYTES = 10 * 1024 * 1024;
const MAX_KEYWORDS = 100;
const MAX_CONTENT_LENGTH = 10_000;
const MAX_NOTES_LENGTH = 5_000;
const MAX_KEYWORD_TEXT_LENGTH = 4_000;

type LensCard = {
  number: number;
  title: string;
  content: string;
  keywords: string[];
  notes: string;
  favorite: boolean;
  updatedAt: string | null;
};

type LensDraft = Omit<LensCard, "keywords"> & { keywordText: string };
type Filter = "all" | "filled" | "empty" | "favorites";
type ImportMode = "merge" | "replace";

type ExportPayload = {
  appId: "art-of-game-design-lens-notes";
  schemaVersion: 1;
  edition: 2;
  language: "ko";
  exportedAt: string;
  lenses: LensCard[];
};

const createEmptyLens = (number: number): LensCard => ({
  number,
  title: "",
  content: "",
  keywords: [],
  notes: "",
  favorite: false,
  updatedAt: null,
});

const createEmptyLibrary = () =>
  Array.from({ length: TOTAL_LENSES }, (_, index) => createEmptyLens(index + 1));

const normalize = (value: string) =>
  value
    .normalize("NFKC")
    .toLocaleLowerCase("ko-KR")
    .replace(/\s+/g, " ")
    .trim();

const compact = (value: string) => normalize(value).replace(/\s/g, "");

const markdownPreviewComponents: Components = {
  p: ({ children }) => <>{children} </>,
  h1: ({ children }) => <>{children} </>,
  h2: ({ children }) => <>{children} </>,
  h3: ({ children }) => <>{children} </>,
  h4: ({ children }) => <>{children} </>,
  h5: ({ children }) => <>{children} </>,
  h6: ({ children }) => <>{children} </>,
  ul: ({ children }) => <>{children}</>,
  ol: ({ children }) => <>{children}</>,
  li: ({ children }) => <>• {children} </>,
  blockquote: ({ children }) => <>{children} </>,
  pre: ({ children }) => <>{children} </>,
  table: ({ children }) => <>{children}</>,
  thead: ({ children }) => <>{children}</>,
  tbody: ({ children }) => <>{children}</>,
  tr: ({ children }) => <>{children} </>,
  th: ({ children }) => <>{children}: </>,
  td: ({ children }) => <>{children} </>,
  input: ({ checked }) => <>{checked ? "☑ " : "☐ "}</>,
  a: ({ children }) => <span className="card-preview-link">{children}</span>,
  img: ({ alt }) => <>{alt ?? ""}</>,
  hr: () => <> · </>,
};

const isFilled = (lens: LensCard) =>
  Boolean(
    lens.title.trim() ||
      lens.content.trim() ||
      lens.keywords.length ||
      lens.notes.trim(),
  );

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const cleanString = (value: unknown) =>
  typeof value === "string" ? value : "";

const cleanLens = (value: unknown): LensCard | null => {
  if (!isRecord(value)) return null;

  const number = value.number;
  const content = value.content ?? value.body;
  const notes = value.notes ?? value.memo;
  const updatedAt = value.updatedAt;

  if (
    !Number.isInteger(number) ||
    (number as number) < 1 ||
    (number as number) > TOTAL_LENSES ||
    typeof value.title !== "string" ||
    typeof content !== "string" ||
    !Array.isArray(value.keywords) ||
    value.keywords.length > MAX_KEYWORDS ||
    !value.keywords.every((keyword) => typeof keyword === "string") ||
    typeof notes !== "string" ||
    typeof value.favorite !== "boolean" ||
    !(updatedAt === null || typeof updatedAt === "string")
  ) return null;

  const keywords = value.keywords
    .map((keyword) => cleanString(keyword).trim())
    .filter(Boolean);

  return {
    number: number as number,
    title: value.title,
    content,
    keywords: [...new Set(keywords)],
    notes,
    favorite: value.favorite,
    updatedAt,
  };
};

const parseLensValues = (values: unknown[], requireComplete = false) => {
  const cleaned = values.map(cleanLens);
  if (cleaned.some((lens) => lens === null)) return null;

  const lenses = cleaned as LensCard[];
  const numbers = new Set(lenses.map((lens) => lens.number));
  if (numbers.size !== lenses.length) return null;
  if (requireComplete && (lenses.length !== TOTAL_LENSES || numbers.size !== TOTAL_LENSES)) {
    return null;
  }
  return lenses;
};

const parsePayload = (value: unknown) =>
  isRecord(value) &&
  value.appId === "art-of-game-design-lens-notes" &&
  value.schemaVersion === 1 &&
  value.edition === 2 &&
  value.language === "ko" &&
  Array.isArray(value.lenses)
    ? parseLensValues(value.lenses, true)
    : null;

const buildLibrary = (values: LensCard[]) => {
  const library = createEmptyLibrary();
  values.forEach((lens) => {
    library[lens.number - 1] = lens;
  });
  return library;
};

const buildDefaultLibrary = (
  values: Array<Omit<LensCard, "favorite"> & { favorite?: boolean }>,
) =>
  buildLibrary(
    values.map((lens) => ({
      ...lens,
      favorite: lens.favorite ?? false,
    })),
  );

const toPayload = (lenses: LensCard[]): ExportPayload => ({
  appId: "art-of-game-design-lens-notes",
  schemaVersion: 1,
  edition: 2,
  language: "ko",
  exportedAt: new Date().toISOString(),
  lenses,
});

const formatClock = (value: Date | null) =>
  value
    ? new Intl.DateTimeFormat("ko-KR", { hour: "2-digit", minute: "2-digit" }).format(value)
    : "";

const formatBackupDate = (value: string | null) => {
  if (!value) return "백업 기록 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "백업 기록 없음";
  return new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric" }).format(date);
};

const makeDraft = (lens: LensCard): LensDraft => ({
  ...lens,
  keywordText: lens.keywords.join(", "),
});

const draftHasChanges = (draft: LensDraft | null, original: LensCard | null) =>
  Boolean(draft && original && JSON.stringify(draft) !== JSON.stringify(makeDraft(original)));

export function LensLibrary({
  lenses: defaultLenses,
}: {
  lenses: Array<Omit<LensCard, "favorite"> & { favorite?: boolean }>;
}) {
  const [lenses, setLenses] = useState<LensCard[]>(() =>
    buildDefaultLibrary(defaultLenses),
  );
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [ready, setReady] = useState(false);
  const [storageLocked, setStorageLocked] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [backupAt, setBackupAt] = useState<string | null>(null);
  const [sessionStartedAt] = useState(Date.now);
  const [notice, setNotice] = useState("");
  const [viewerNumber, setViewerNumber] = useState<number | null>(null);
  const [editorNumber, setEditorNumber] = useState<number | null>(null);
  const [draft, setDraft] = useState<LensDraft | null>(null);

  const searchRef = useRef<HTMLInputElement>(null);
  const titleRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const viewerPanelRef = useRef<HTMLElement>(null);
  const viewerCloseRef = useRef<HTMLButtonElement>(null);
  const editorPanelRef = useRef<HTMLElement>(null);
  const importModeRef = useRef<ImportMode>("merge");
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const viewerOwnsHistoryRef = useRef(false);
  const closingViewerRef = useRef(false);
  const closingEditorRef = useRef(false);
  const initialHashHandledRef = useRef(false);

  const persistLibrary = useCallback((
    next: LensCard[],
    force = false,
    changedNumbers: number[] = [],
  ) => {
    if (storageLocked && !force) {
      setSaveState("error");
      setNotice("기존 저장 데이터에 오류가 있어 덮어쓰지 않았습니다. 정상 백업을 가져오거나 브라우저 데이터를 초기화해 주세요.");
      return null;
    }

    try {
      let valueToPersist = next;
      if (!force && changedNumbers.length > 0) {
        const currentStored = window.localStorage.getItem(STORAGE_KEY);
        if (currentStored) {
          const currentValues = parsePayload(JSON.parse(currentStored));
          if (!currentValues) throw new Error("invalid-current-storage");

          valueToPersist = buildLibrary(currentValues);
          changedNumbers.forEach((number) => {
            valueToPersist[number - 1] = next[number - 1];
          });
        }
      }

      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(toPayload(valueToPersist)),
      );
      setSavedAt(new Date());
      setSaveState("saved");
      return valueToPersist;
    } catch {
      setSaveState("error");
      setNotice("저장에 실패했습니다. 다른 탭을 닫은 뒤 JSON 백업을 내보내고 다시 시도해 주세요.");
      return null;
    }
  }, [storageLocked]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const stored = window.localStorage.getItem(STORAGE_KEY);
        if (stored) {
          const parsed: unknown = JSON.parse(stored);
          const values = parsePayload(parsed);
          if (!values) throw new Error("invalid-stored-data");

          setLenses(buildLibrary(values));
          setSavedAt(new Date());
          setSaveState("saved");
        }
        setBackupAt(window.localStorage.getItem(BACKUP_DATE_KEY));
      } catch {
        setStorageLocked(true);
        setNotice("저장된 데이터가 손상되어 자동 덮어쓰기를 중단했습니다. 이 사이트에서 만든 정상 JSON 백업을 가져와 복구해 주세요.");
        setSaveState("error");
      } finally {
        setReady(true);
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const handleShortcut = (event: globalThis.KeyboardEvent) => {
      if (
        viewerNumber === null &&
        editorNumber === null &&
        (event.metaKey || event.ctrlKey) &&
        event.key.toLowerCase() === "k"
      ) {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [editorNumber, viewerNumber]);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== STORAGE_KEY || !event.newValue) return;

      try {
        const values = parsePayload(JSON.parse(event.newValue));
        if (!values) throw new Error("invalid-storage-event");

        setLenses(buildLibrary(values));
        setStorageLocked(false);
        setSavedAt(new Date());
        setSaveState("saved");
        if (editorNumber !== null) {
          setNotice("다른 탭의 최신 저장 내용을 반영했습니다. 현재 편집 중인 렌즈는 저장할 때 그 위에 병합됩니다.");
        }
      } catch {
        setStorageLocked(true);
        setSaveState("error");
        setNotice("다른 탭에서 잘못된 저장 데이터가 감지되어 덮어쓰기를 중단했습니다.");
      }
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, [editorNumber]);

  const originalLens = useMemo(
    () => (editorNumber === null ? null : lenses[editorNumber - 1] ?? null),
    [editorNumber, lenses],
  );

  const viewedLens = useMemo(
    () => (viewerNumber === null ? null : lenses[viewerNumber - 1] ?? null),
    [lenses, viewerNumber],
  );

  const restoreTriggerFocus = useCallback(() => {
    window.setTimeout(() => {
      if (returnFocusRef.current?.isConnected) {
        returnFocusRef.current.focus();
      } else {
        searchRef.current?.focus();
      }
    }, 0);
  }, []);

  const dismissViewer = useCallback(() => {
    setViewerNumber(null);
    restoreTriggerFocus();
  }, [restoreTriggerFocus]);

  const closeViewer = useCallback(() => {
    if (viewerOwnsHistoryRef.current) {
      closingViewerRef.current = true;
      viewerOwnsHistoryRef.current = false;
      window.history.back();
      return;
    }

    setViewerNumber(null);
    window.history.replaceState(
      null,
      "",
      window.location.pathname + window.location.search,
    );
    restoreTriggerFocus();
  }, [restoreTriggerFocus]);

  const openViewer = useCallback((number: number, source?: HTMLElement | null) => {
    const lens = lenses[number - 1];
    if (!lens) return;

    returnFocusRef.current = source ?? (document.activeElement as HTMLElement | null);
    setViewerNumber(number);

    const nextHash = "#lens-" + number;
    if (window.location.hash !== nextHash) {
      const historyState = isRecord(window.history.state)
        ? window.history.state
        : {};
      window.history.pushState(
        { ...historyState, lensViewer: number },
        "",
        nextHash,
      );
      viewerOwnsHistoryRef.current = true;
    } else {
      viewerOwnsHistoryRef.current = false;
    }

    window.requestAnimationFrame(() => viewerCloseRef.current?.focus());
  }, [lenses]);

  const moveViewer = useCallback((direction: -1 | 1) => {
    setViewerNumber((current) => {
      if (current === null) return current;
      const next = Math.min(TOTAL_LENSES, Math.max(1, current + direction));
      if (next === current) return current;

      const historyState = isRecord(window.history.state)
        ? window.history.state
        : {};
      window.history.replaceState(
        viewerOwnsHistoryRef.current
          ? { ...historyState, lensViewer: next }
          : historyState,
        "",
        "#lens-" + next,
      );
      return next;
    });
  }, []);

  useEffect(() => {
    if (viewerNumber === null) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.requestAnimationFrame(() => viewerCloseRef.current?.focus());

    const handleViewerKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.isComposing) return;
      if (event.key === "Escape") {
        event.preventDefault();
        closeViewer();
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        moveViewer(-1);
        return;
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        moveViewer(1);
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = viewerPanelRef.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable?.length) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    const handlePopState = () => {
      if (closingViewerRef.current) closingViewerRef.current = false;
      dismissViewer();
    };

    window.addEventListener("keydown", handleViewerKeyDown);
    window.addEventListener("popstate", handlePopState);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleViewerKeyDown);
      window.removeEventListener("popstate", handlePopState);
    };
  }, [closeViewer, dismissViewer, moveViewer, viewerNumber]);

  const dismissEditor = useCallback(() => {
    setEditorNumber(null);
    setDraft(null);
    window.setTimeout(() => {
      if (returnFocusRef.current?.isConnected) {
        returnFocusRef.current.focus();
      } else {
        searchRef.current?.focus();
      }
    }, 0);
  }, []);

  const closeEditor = useCallback(
    (force = false) => {
      if (
        !force &&
        draftHasChanges(draft, originalLens) &&
        !window.confirm("저장하지 않은 변경사항이 있습니다. 편집을 닫을까요?")
      ) return;

      const ownsHistoryEntry =
        isRecord(window.history.state) &&
        window.history.state.lensEditor === editorNumber;
      if (ownsHistoryEntry) {
        closingEditorRef.current = true;
        window.history.back();
      } else {
        dismissEditor();
        window.history.replaceState(
          window.history.state,
          "",
          window.location.pathname + window.location.search,
        );
      }
    },
    [dismissEditor, draft, editorNumber, originalLens],
  );

  useEffect(() => {
    if (editorNumber === null) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleEditorKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.isComposing) return;
      if (event.key === "Escape") {
        closeEditor();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = editorPanelRef.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable?.length) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    window.addEventListener("keydown", handleEditorKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleEditorKeyDown);
    };
  }, [closeEditor, editorNumber]);

  useEffect(() => {
    if (editorNumber === null) return;
    const hasUnsavedChanges = draftHasChanges(draft, originalLens);

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!hasUnsavedChanges) return;
      event.preventDefault();
      event.returnValue = "";
    };

    const handlePopState = () => {
      if (closingEditorRef.current) {
        closingEditorRef.current = false;
        dismissEditor();
        return;
      }

      if (
        hasUnsavedChanges &&
        !window.confirm("저장하지 않은 변경사항이 있습니다. 편집을 닫을까요?")
      ) {
        const historyState = isRecord(window.history.state)
          ? window.history.state
          : {};
        window.history.pushState(
          { ...historyState, lensEditor: editorNumber },
          "",
          `#lens-${editorNumber}`,
        );
        return;
      }
      dismissEditor();
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      window.removeEventListener("popstate", handlePopState);
    };
  }, [dismissEditor, draft, editorNumber, originalLens]);

  const openEditor = useCallback((
    number: number,
    source?: HTMLElement | null,
    fromViewer = false,
  ) => {
    const lens = lenses[number - 1];
    if (!lens) return;

    if (!fromViewer) {
      returnFocusRef.current = source ?? (document.activeElement as HTMLElement | null);
    }
    setViewerNumber(null);
    setEditorNumber(number);
    setDraft(makeDraft(lens));

    const nextHash = "#lens-" + number;
    const historyState = isRecord(window.history.state)
      ? window.history.state
      : {};

    if (fromViewer) {
      const viewerOwnsHistory = viewerOwnsHistoryRef.current;
      viewerOwnsHistoryRef.current = false;
      window.history.replaceState(
        {
          ...historyState,
          lensViewer: undefined,
          lensEditor: viewerOwnsHistory ? number : undefined,
        },
        "",
        nextHash,
      );
    } else if (window.location.hash !== nextHash) {
      window.history.pushState(
        { ...historyState, lensEditor: number },
        "",
        nextHash,
      );
    }
    window.setTimeout(() => titleRef.current?.focus(), 0);
  }, [lenses]);

  useEffect(() => {
    if (!ready || initialHashHandledRef.current) return;
    initialHashHandledRef.current = true;
    const match = window.location.hash.match(/^#lens-(\d{1,3})$/);
    const number = match ? Number(match[1]) : 0;
    if (number < 1 || number > TOTAL_LENSES) return;

    const timer = window.setTimeout(() => openViewer(number), 0);
    return () => window.clearTimeout(timer);
  }, [openViewer, ready]);

  const stats = useMemo(() => {
    const filled = lenses.filter(isFilled).length;
    const favorites = lenses.filter((lens) => lens.favorite).length;
    return {
      filled,
      empty: TOTAL_LENSES - filled,
      favorites,
      percent: Math.round((filled / TOTAL_LENSES) * 100),
    };
  }, [lenses]);

  const filteredLenses = useMemo(() => {
    const normalizedQuery = normalize(query);
    const numberMatch = normalizedQuery.match(/^#?\s*(\d{1,3})$/);
    const exactNumber = numberMatch ? Number(numberMatch[1]) : null;
    const tokens = normalizedQuery.split(" ").filter(Boolean);

    return lenses.filter((lens) => {
      if (filter === "filled" && !isFilled(lens)) return false;
      if (filter === "empty" && isFilled(lens)) return false;
      if (filter === "favorites" && !lens.favorite) return false;
      if (!normalizedQuery) return true;
      if (exactNumber !== null) return lens.number === exactNumber;

      const haystack = normalize([
        lens.number,
        lens.title,
        lens.content,
        lens.keywords.join(" "),
        lens.notes,
      ].join(" "));
      const compactHaystack = compact(haystack);
      return tokens.every((token) =>
        haystack.includes(token) || compactHaystack.includes(compact(token)),
      );
    });
  }, [filter, lenses, query]);

  const saveDraft = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draft || editorNumber === null) return;

    const keywords = [...new Set(
      draft.keywordText
        .split(/[,\n]/)
        .map((keyword) => keyword.trim())
        .filter(Boolean),
    )];
    if (keywords.length > MAX_KEYWORDS) {
      setNotice(`키워드는 최대 ${MAX_KEYWORDS}개까지 저장할 수 있습니다.`);
      return;
    }

    const updatedLens: LensCard = {
      number: editorNumber,
      title: draft.title.trim(),
      content: draft.content.trim(),
      keywords,
      notes: draft.notes.trim(),
      favorite: draft.favorite,
      updatedAt: new Date().toISOString(),
    };
    const next = lenses.map((lens) =>
      lens.number === editorNumber ? updatedLens : lens,
    );

    const persisted = persistLibrary(next, false, [editorNumber]);
    if (!persisted) return;
    setLenses(persisted);
    setNotice(`렌즈 #${editorNumber}을 저장했습니다.`);
    closeEditor(true);
  };

  const toggleFavorite = (number: number) => {
    const next = lenses.map((lens) =>
      lens.number === number
        ? { ...lens, favorite: !lens.favorite, updatedAt: new Date().toISOString() }
        : lens,
    );
    const persisted = persistLibrary(next, false, [number]);
    if (persisted) setLenses(persisted);
  };

  const downloadPayload = (payload: ExportPayload, prefix = "lens-notes") => {
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${prefix}-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  };

  const exportLibrary = () => {
    downloadPayload(toPayload(lenses));
    const now = new Date().toISOString();
    try {
      window.localStorage.setItem(BACKUP_DATE_KEY, now);
      setBackupAt(now);
      setNotice("JSON 백업 다운로드를 시작했습니다.");
    } catch {
      setNotice("백업 다운로드는 시작했지만 이 브라우저에 백업 날짜를 기록하지 못했습니다.");
    }
  };

  const restoreDefaults = () => {
    if (
      !window.confirm(
        "이 브라우저에서 수정한 내용을 지우고 운영자가 공개한 기본값으로 복원할까요?",
      )
    ) return;

    try {
      window.localStorage.removeItem(STORAGE_KEY);
      const restored = buildDefaultLibrary(defaultLenses);
      setLenses(restored);
      setStorageLocked(false);
      setSavedAt(null);
      setSaveState("idle");
      setNotice("운영자가 공개한 기본 렌즈로 복원했습니다.");
    } catch {
      setNotice("기본값으로 복원하지 못했습니다. 브라우저 저장 공간을 확인해 주세요.");
    }
  };

  const requestImport = (mode: ImportMode) => {
    importModeRef.current = mode;
    fileInputRef.current?.click();
  };

  const importLibrary = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    try {
      if (file.size > MAX_IMPORT_BYTES) throw new Error("file-too-large");
      const parsed: unknown = JSON.parse(await file.text());
      const imported = parsePayload(parsed);
      if (!imported) throw new Error("invalid-format");

      const mode = importModeRef.current;
      const importedWithData = imported.filter(
        (lens) => isFilled(lens) || lens.favorite,
      );
      const affected = mode === "replace" ? imported.length : importedWithData.length;
      if (mode === "merge" && affected === 0) {
        setNotice("병합할 작성 내용이나 즐겨찾기가 백업에 없습니다.");
        return;
      }

      const message = mode === "replace"
        ? `현재 데이터를 지우고 ${affected}개 슬롯으로 교체할까요?`
        : `작성된 ${affected}개 항목을 병합할까요? 같은 번호는 백업 내용으로 바뀝니다.`;
      if (!window.confirm(`${message} 가져오기 전 현재 데이터는 자동으로 백업됩니다.`)) {
        return;
      }

      const currentPayload = toPayload(lenses);
      try {
        window.localStorage.setItem(
          IMPORT_BACKUP_KEY,
          JSON.stringify(currentPayload),
        );
      } catch {
        downloadPayload(currentPayload, "lens-notes-before-import");
        setNotice("내부 안전 백업을 만들지 못해 가져오기를 취소했습니다. 현재 데이터의 JSON 다운로드는 시작했습니다.");
        return;
      }
      downloadPayload(currentPayload, "lens-notes-before-import");

      const next = mode === "replace"
        ? buildLibrary(imported)
        : (() => {
            const merged = [...lenses];
            importedWithData.forEach((lens) => {
              merged[lens.number - 1] = lens;
            });
            return merged;
          })();

      const persisted = persistLibrary(next, true);
      if (!persisted) return;
      setStorageLocked(false);
      setLenses(persisted);
      setNotice(
        mode === "replace"
          ? "113개 렌즈 슬롯을 교체했습니다. 기존 데이터도 백업했습니다."
          : `${affected}개 항목을 병합했습니다. 기존 데이터도 백업했습니다.`,
      );
    } catch {
      setNotice("가져오지 못했습니다. 이 사이트에서 내보낸 10MB 이하의 JSON 백업인지 확인해 주세요.");
    }
  };

  const handleSearchKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape" && query) setQuery("");
  };

  const filterItems: { value: Filter; label: string; count: number }[] = [
    { value: "all", label: "전체", count: TOTAL_LENSES },
    { value: "filled", label: "작성됨", count: stats.filled },
    { value: "empty", label: "비어 있음", count: stats.empty },
    { value: "favorites", label: "즐겨찾기", count: stats.favorites },
  ];

  const backupIsOld = useMemo(() => {
    if (!backupAt) return true;
    const backupTime = new Date(backupAt).getTime();
    return Number.isNaN(backupTime) ||
      sessionStartedAt - backupTime > 7 * 24 * 60 * 60 * 1000;
  }, [backupAt, sessionStartedAt]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="렌즈 노트 처음으로">
          <span className="brand-mark" aria-hidden="true">L</span>
          <span>
            <strong>렌즈 노트</strong>
            <small>개인 게임 디자인 서재</small>
          </span>
        </a>

        <div className="topbar-actions">
          <span className={`save-status save-status--${saveState}`} aria-live="polite">
            <i aria-hidden="true" />
            {saveState === "saving" && "저장 중"}
            {saveState === "saved" && `저장됨 ${formatClock(savedAt)}`}
            {saveState === "error" && "저장 실패"}
            {saveState === "idle" && "이 기기에 저장"}
          </span>
          <button className="button button--quiet" type="button" onClick={() => requestImport("merge")}>
            가져오기
          </button>
          <button className="button button--quiet" type="button" onClick={restoreDefaults}>
            기본값 복원
          </button>
          <button className="button button--dark" type="button" onClick={exportLibrary}>
            백업하기
          </button>
          <input
            ref={fileInputRef}
            className="sr-only"
            type="file"
            accept="application/json,.json"
            onChange={importLibrary}
            aria-label="렌즈 JSON 파일 선택"
          />
        </div>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow">THE ART OF GAME DESIGN · SECOND EDITION INDEX</p>
          <h1>필요한 관점을,<br /><em>필요한 순간에.</em></h1>
          <p className="hero-description">
            113개의 렌즈를 나만의 언어로 기록하고, 번호와 키워드로 바로 찾아보세요.
            책의 내용은 포함되어 있지 않습니다.
          </p>
        </div>

        <div className="hero-progress" aria-label={`전체 113개 중 ${stats.filled}개 작성됨`}>
          <div className="progress-orbit"><span>{stats.percent}<small>%</small></span></div>
          <div><strong>{stats.filled} / {TOTAL_LENSES}</strong><p>렌즈 작성 완료</p></div>
        </div>
      </section>

      <section className="workspace" aria-label="렌즈 검색과 목록">
        <div className="search-panel">
          <label className="search-box" htmlFor="lens-search">
            <span className="search-symbol" aria-hidden="true">⌕</span>
            <span className="sr-only">번호 또는 키워드 검색</span>
            <input
              ref={searchRef}
              id="lens-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={handleSearchKeyDown}
              placeholder="번호 또는 키워드 검색"
              autoComplete="off"
            />
            <kbd aria-hidden="true">Ctrl K</kbd>
          </label>

          <div className="filter-row" role="group" aria-label="렌즈 상태 필터">
            {filterItems.map((item) => (
              <button
                key={item.value}
                type="button"
                className={filter === item.value ? "filter-chip is-active" : "filter-chip"}
                aria-pressed={filter === item.value}
                onClick={() => setFilter(item.value)}
              >
                {item.label}<span>{item.count}</span>
              </button>
            ))}
          </div>
        </div>

        <aside className="privacy-note">
          <div>
            <span className="privacy-icon" aria-hidden="true">⌂</span>
            <p><strong>공개 기본값에서 자유롭게 편집할 수 있습니다.</strong> 수정본은 이 브라우저에만 저장되며 다른 사람에게는 영향을 주지 않아요.</p>
          </div>
          <button
            type="button"
            className={backupIsOld ? "backup-pill is-needed" : "backup-pill"}
            onClick={exportLibrary}
            aria-label={
              backupIsOld
                ? "JSON 백업하기, 백업이 필요합니다"
                : `JSON 백업하기, 마지막 백업 ${formatBackupDate(backupAt)}`
            }
          >
            {backupIsOld ? "백업 필요" : formatBackupDate(backupAt)}
          </button>
        </aside>

        {notice && (
          <div className="notice" role="status">
            <span>{notice}</span>
            <button type="button" onClick={() => setNotice("")} aria-label="알림 닫기">×</button>
          </div>
        )}

        {stats.filled === 0 && !query && filter === "all" && (
          <section className="first-run">
            <div>
              <span className="first-run-number">001</span>
              <h2>빈 카드부터 시작해볼까요?</h2>
              <p>제목, 본문, 키워드, 나만의 메모를 입력할 수 있습니다.</p>
            </div>
            <div className="first-run-actions">
              <button
                type="button"
                className="button button--accent"
                onClick={(event) => openEditor(1, event.currentTarget)}
              >
                1번 렌즈 입력
              </button>
              <button type="button" className="text-button" onClick={() => requestImport("replace")}>
                기존 JSON으로 시작
              </button>
            </div>
          </section>
        )}

        <div className="results-heading">
          <div>
            <p className="section-kicker">LENS CATALOGUE</p>
            <h2>{query ? `“${query}” 검색 결과` : "렌즈 목록"}</h2>
          </div>
          <p aria-live="polite" aria-atomic="true">
            <strong>{filteredLenses.length}</strong>개 표시 중
          </p>
        </div>

        {filteredLenses.length ? (
          <div className="lens-grid">
            {filteredLenses.map((lens) => {
              const filled = isFilled(lens);
              const preview = lens.content || lens.notes ||
                "책을 읽으며 확인한 내용이나 나만의 요약을 기록해 보세요.";
              return (
                <article
                  key={lens.number}
                  className={filled ? "lens-card is-filled" : "lens-card is-empty"}
                >
                  <div className="card-topline">
                    <span className="card-number">#{lens.number.toString().padStart(3, "0")}</span>
                    <button
                      type="button"
                      className={lens.favorite ? "favorite-button is-favorite" : "favorite-button"}
                      onClick={() => toggleFavorite(lens.number)}
                      aria-label={lens.favorite
                        ? `${lens.number}번 즐겨찾기 해제`
                        : `${lens.number}번 즐겨찾기 추가`}
                      aria-pressed={lens.favorite}
                    >
                      {lens.favorite ? "★" : "☆"}
                    </button>
                  </div>

                  <button
                    type="button"
                    className="card-open"
                    onClick={(event) => openViewer(lens.number, event.currentTarget)}
                    aria-label={`${lens.number}번 렌즈${lens.title ? `, ${lens.title}` : ""} ${filled ? "보기" : "빈 카드 보기"}`}
                  >
                    <span className="card-status">{filled ? "작성됨" : "비어 있음"}</span>
                    <strong>{lens.title || "렌즈 제목을 입력하세요"}</strong>
                    <span className="card-preview">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        skipHtml
                        components={markdownPreviewComponents}
                      >
                        {preview}
                      </ReactMarkdown>
                    </span>
                    {lens.keywords.length > 0 && (
                      <span className="keyword-list" aria-label="키워드">
                        {lens.keywords.slice(0, 3).map((keyword) => <i key={keyword}>{keyword}</i>)}
                        {lens.keywords.length > 3 && <i>+{lens.keywords.length - 3}</i>}
                      </span>
                    )}
                    <span className="card-action">
                      {filled ? "내용 보기" : "빈 카드 보기"}<b aria-hidden="true">↗</b>
                    </span>
                  </button>
                </article>
              );
            })}
          </div>
        ) : (
          <section className="no-results">
            <span aria-hidden="true">0</span>
            <h3>일치하는 렌즈가 없습니다.</h3>
            <p>검색어를 바꾸거나 상태 필터를 초기화해 보세요.</p>
            <button
              type="button"
              className="button button--dark"
              onClick={() => { setQuery(""); setFilter("all"); }}
            >
              검색 초기화
            </button>
          </section>
        )}
      </section>

      <footer className="footer">
        <p>PUBLIC LENS NOTE TOOL</p>
        <span>운영자의 기본값 위에 나만의 수정본이 이 브라우저에 저장됩니다.</span>
        <div className="footer-actions">
          <button type="button" onClick={restoreDefaults}>기본값 복원</button>
          <button type="button" onClick={() => requestImport("merge")}>JSON 병합</button>
          <button type="button" onClick={() => requestImport("replace")}>JSON으로 전체 교체</button>
        </div>
      </footer>

      {viewerNumber !== null && viewedLens && (
        <div
          className="viewer-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeViewer();
          }}
        >
          <section
            ref={viewerPanelRef}
            className="viewer-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="viewer-heading"
          >
            <header className="viewer-header">
              <div>
                <p>LENS #{viewerNumber.toString().padStart(3, "0")}</p>
                <h2 id="viewer-heading">
                  {viewedLens.title || "렌즈 " + viewerNumber}
                </h2>
              </div>
              <button
                ref={viewerCloseRef}
                type="button"
                className="viewer-close"
                onClick={closeViewer}
                aria-label="보기 닫기"
              >
                ×
              </button>
            </header>

            <div className="viewer-scroll">
              {viewedLens.content.trim() ? (
                <section className="viewer-section">
                  <div className="markdown-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>
                      {viewedLens.content}
                    </ReactMarkdown>
                  </div>
                </section>
              ) : (
                <div className="viewer-empty">
                  <strong>아직 작성된 내용이 없습니다.</strong>
                  <p>편집 버튼을 눌러 이 렌즈에 내용을 추가할 수 있습니다.</p>
                </div>
              )}

              {viewedLens.keywords.length > 0 && (
                <section className="viewer-section viewer-keyword-section">
                  <h3>검색 키워드</h3>
                  <ul className="viewer-keywords">
                    {viewedLens.keywords.map((keyword) => (
                      <li key={keyword}>#{keyword}</li>
                    ))}
                  </ul>
                </section>
              )}

              {viewedLens.notes.trim() && (
                <section className="viewer-section viewer-notes">
                  <h3>메모</h3>
                  <div className="markdown-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>
                      {viewedLens.notes}
                    </ReactMarkdown>
                  </div>
                </section>
              )}
            </div>

            <footer className="viewer-footer">
              <button
                type="button"
                className="viewer-nav-button"
                onClick={() => moveViewer(-1)}
                disabled={viewerNumber <= 1}
              >
                <span aria-hidden="true">←</span>
                이전 렌즈
              </button>
              <button
                type="button"
                className="button button--accent viewer-edit-button"
                onClick={() => openEditor(viewerNumber, null, true)}
              >
                편집
              </button>
              <button
                type="button"
                className="viewer-nav-button viewer-nav-button--next"
                onClick={() => moveViewer(1)}
                disabled={viewerNumber >= TOTAL_LENSES}
              >
                다음 렌즈
                <span aria-hidden="true">→</span>
              </button>
            </footer>
            <p className="viewer-shortcut" aria-hidden="true">
              키보드 ← → 로 이동 · Esc로 닫기
            </p>
          </section>
        </div>
      )}

      {editorNumber !== null && draft && (
        <div
          className="editor-backdrop"
          onMouseDown={(event) => { if (event.target === event.currentTarget) closeEditor(); }}
        >
          <aside
            ref={editorPanelRef}
            className="editor-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="editor-heading"
          >
            <form onSubmit={saveDraft}>
              <header className="editor-header">
                <div>
                  <p>개인 렌즈 카드</p>
                  <h2 id="editor-heading">Lens #{editorNumber.toString().padStart(3, "0")}</h2>
                </div>
                <button
                  type="button"
                  className="editor-close"
                  onClick={() => closeEditor()}
                  aria-label="편집 닫기"
                >
                  ×
                </button>
              </header>

              <div className="editor-scroll">
                <label className="field">
                  <span>렌즈 제목</span>
                  <input
                    ref={titleRef}
                    value={draft.title}
                    onChange={(event) => setDraft({ ...draft, title: event.target.value })}
                    placeholder="예: 렌즈 이름"
                    maxLength={200}
                  />
                </label>

                <label className="field field--large">
                  <span>내용 <small>마크다운 지원</small></span>
                  <textarea
                    value={draft.content}
                    onChange={(event) => setDraft({ ...draft, content: event.target.value })}
                    placeholder="책에서 확인한 내용이나 나만의 요약을 입력하세요."
                    maxLength={MAX_CONTENT_LENGTH}
                    rows={11}
                  />
                </label>

                <label className="field">
                  <span>검색 키워드 <small>쉼표로 구분</small></span>
                  <input
                    value={draft.keywordText}
                    onChange={(event) => setDraft({ ...draft, keywordText: event.target.value })}
                    placeholder="몰입, 선택, 피드백"
                    maxLength={MAX_KEYWORD_TEXT_LENGTH}
                  />
                </label>

                <label className="field">
                  <span>나만의 메모 <small>마크다운 지원</small></span>
                  <textarea
                    value={draft.notes}
                    onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
                    placeholder="이 렌즈를 내 프로젝트에 어떻게 적용할지 기록하세요."
                    maxLength={MAX_NOTES_LENGTH}
                    rows={5}
                  />
                </label>

                <label className="favorite-toggle">
                  <input
                    type="checkbox"
                    checked={draft.favorite}
                    onChange={(event) => setDraft({ ...draft, favorite: event.target.checked })}
                  />
                  <span aria-hidden="true">★</span>
                  자주 보는 렌즈로 표시
                </label>
              </div>

              <footer className="editor-footer">
                <p>저장하면 이 브라우저에 자동 보관됩니다.</p>
                <div>
                  <button type="button" className="button button--quiet" onClick={() => closeEditor()}>
                    취소
                  </button>
                  <button type="submit" className="button button--accent">렌즈 저장</button>
                </div>
              </footer>
            </form>
          </aside>
        </div>
      )}
    </main>
  );
}
