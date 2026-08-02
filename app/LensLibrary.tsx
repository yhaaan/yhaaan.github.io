"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { LensCard } from "./lens-data";

const TOTAL_LENSES = 113;

type Filter = "all" | "published" | "upcoming";

const normalize = (value: string) =>
  value
    .normalize("NFKC")
    .toLocaleLowerCase("ko-KR")
    .replace(/\s+/g, " ")
    .trim();

const compact = (value: string) => normalize(value).replace(/\s/g, "");

const isPublished = (lens: LensCard) =>
  Boolean(
    lens.title.trim() ||
      lens.content.trim() ||
      lens.keywords.length ||
      lens.notes.trim(),
  );

const lensNumberFromHash = (hash: string) => {
  const match = hash.match(/^#lens-(\d{1,3})$/);
  if (!match) return null;

  const number = Number(match[1]);
  return number >= 1 && number <= TOTAL_LENSES ? number : null;
};

const numberLabel = (number: number) => String(number).padStart(3, "0");

export function LensLibrary({ lenses }: { lenses: LensCard[] }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [selectedNumber, setSelectedNumber] = useState<number | null>(null);

  const searchRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const pushedHistoryRef = useRef(false);

  const stats = useMemo(() => {
    const published = lenses.filter(isPublished).length;
    return { published, upcoming: TOTAL_LENSES - published };
  }, [lenses]);

  const filteredLenses = useMemo(() => {
    const normalizedQuery = normalize(query);
    const numericMatch = normalizedQuery.match(/^#?\s*(\d{1,3})$/);
    const exactNumber = numericMatch ? Number(numericMatch[1]) : null;
    const terms = normalizedQuery.split(" ").filter(Boolean);

    return lenses.filter((lens) => {
      const published = isPublished(lens);

      if (filter === "published" && !published) return false;
      if (filter === "upcoming" && published) return false;
      if (!normalizedQuery) return true;
      if (exactNumber !== null) return lens.number === exactNumber;

      const haystack = normalize(
        [
          lens.number,
          `#${lens.number}`,
          lens.title,
          lens.content,
          lens.keywords.join(" "),
          lens.notes,
        ].join(" "),
      );
      const compactHaystack = compact(haystack);

      return terms.every(
        (term) =>
          haystack.includes(term) || compactHaystack.includes(compact(term)),
      );
    });
  }, [filter, lenses, query]);

  const selectedLens =
    selectedNumber === null ? null : lenses[selectedNumber - 1] ?? null;

  const restoreFocus = useCallback(() => {
    const target = returnFocusRef.current;
    returnFocusRef.current = null;
    window.requestAnimationFrame(() => target?.focus());
  }, []);

  const closeLens = useCallback(() => {
    const currentHash =
      selectedNumber === null ? "" : `#lens-${selectedNumber}`;

    if (
      pushedHistoryRef.current &&
      currentHash &&
      window.location.hash === currentHash
    ) {
      pushedHistoryRef.current = false;
      window.history.back();
      return;
    }

    if (window.location.hash.startsWith("#lens-")) {
      window.history.replaceState(
        null,
        "",
        `${window.location.pathname}${window.location.search}`,
      );
    }

    setSelectedNumber(null);
    restoreFocus();
  }, [restoreFocus, selectedNumber]);

  const openLens = useCallback(
    (number: number, trigger: HTMLElement) => {
      const lens = lenses[number - 1];
      if (!lens || !isPublished(lens)) return;

      returnFocusRef.current = trigger;
      const nextHash = `#lens-${number}`;

      if (window.location.hash !== nextHash) {
        window.history.pushState(null, "", nextHash);
        pushedHistoryRef.current = true;
      }

      setSelectedNumber(number);
    },
    [lenses],
  );

  useEffect(() => {
    const syncFromLocation = () => {
      const number = lensNumberFromHash(window.location.hash);
      const lens = number === null ? null : lenses[number - 1];
      const nextNumber = lens && isPublished(lens) ? number : null;
      setSelectedNumber(nextNumber);

      if (nextNumber === null) restoreFocus();
    };

    syncFromLocation();
    window.addEventListener("popstate", syncFromLocation);
    window.addEventListener("hashchange", syncFromLocation);

    return () => {
      window.removeEventListener("popstate", syncFromLocation);
      window.removeEventListener("hashchange", syncFromLocation);
    };
  }, [lenses, restoreFocus]);

  useEffect(() => {
    const handleShortcut = (event: globalThis.KeyboardEvent) => {
      if (
        selectedNumber === null &&
        (event.metaKey || event.ctrlKey) &&
        event.key.toLocaleLowerCase() === "k"
      ) {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [selectedNumber]);

  useEffect(() => {
    if (!selectedLens) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.requestAnimationFrame(() => closeButtonRef.current?.focus());

    const handleDialogKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape" && !event.isComposing) {
        event.preventDefault();
        closeLens();
        return;
      }

      if (event.key !== "Tab") return;

      const focusable = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
        ) ?? [],
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (!dialogRef.current?.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
        return;
      }

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    window.addEventListener("keydown", handleDialogKey);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleDialogKey);
    };
  }, [closeLens, selectedLens]);

  const filters: Array<{ value: Filter; label: string; count: number }> = [
    { value: "all", label: "전체", count: TOTAL_LENSES },
    { value: "published", label: "공개됨", count: stats.published },
    { value: "upcoming", label: "준비 중", count: stats.upcoming },
  ];

  const progress = Math.round((stats.published / TOTAL_LENSES) * 100);
  const hasSearch = query.trim().length > 0;

  return (
    <div className="site-shell">
      <div
        className="page-content"
        inert={selectedLens ? true : undefined}
        aria-hidden={selectedLens ? true : undefined}
      >
      <header className="site-header">
        <div className="brand" aria-label="렌즈 노트">
          <span className="brand-mark" aria-hidden="true">
            L
          </span>
          <span>
            <strong>렌즈 노트</strong>
            <small>GAME DESIGN LENS LIBRARY</small>
          </span>
        </div>
        <div className="read-only-badge">
          <span aria-hidden="true" />
          공개 읽기 전용
        </div>
      </header>

      <main>
        <section className="hero" aria-labelledby="page-title">
          <div className="hero-copy">
            <p className="eyebrow">PUBLIC CREATIVE COLLECTION · 01—113</p>
            <h1 id="page-title">
              생각을 바꾸는 질문을,
              <br />
              하나의 <em>렌즈</em>로.
            </h1>
            <p className="hero-description">
              운영자가 만든 게임 디자인 관점을 번호와 키워드로 탐색하세요.
              모든 방문자에게 같은 내용이 표시됩니다.
            </p>
          </div>

          <aside className="collection-status" aria-label="컬렉션 공개 현황">
            <div className="status-number">
              <strong>{stats.published}</strong>
              <span>/ {TOTAL_LENSES}</span>
            </div>
            <p>현재 공개된 렌즈</p>
            <div
              className="progress-track"
              role="progressbar"
              aria-label="렌즈 공개 진행률"
              aria-valuemin={0}
              aria-valuemax={TOTAL_LENSES}
              aria-valuenow={stats.published}
            >
              <span style={{ width: `${progress}%` }} />
            </div>
            <small>{progress}% PUBLISHED</small>
          </aside>
        </section>

        <section className="library" aria-labelledby="library-title">
          <div className="library-heading">
            <div>
              <p className="section-kicker">BROWSE THE COLLECTION</p>
              <h2 id="library-title">렌즈 찾아보기</h2>
            </div>
            <p>
              번호는 <b>42</b> 또는 <b>#42</b>처럼 입력할 수 있습니다.
            </p>
          </div>

          <div className="search-panel">
            <div className="search-box">
              <label className="sr-only" htmlFor="lens-search">
                렌즈 검색
              </label>
              <span className="search-icon" aria-hidden="true" />
              <input
                id="lens-search"
                ref={searchRef}
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="번호, 제목, 키워드 또는 내용 검색"
                autoComplete="off"
              />
              {hasSearch ? (
                <button
                  type="button"
                  className="clear-search"
                  onClick={() => {
                    setQuery("");
                    searchRef.current?.focus();
                  }}
                  aria-label="검색어 지우기"
                >
                  ×
                </button>
              ) : (
                <kbd aria-hidden="true">Ctrl/⌘ K</kbd>
              )}
            </div>

            <div className="filter-tabs" aria-label="렌즈 공개 상태 필터">
              {filters.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={filter === option.value ? "is-active" : ""}
                  onClick={() => setFilter(option.value)}
                  aria-pressed={filter === option.value}
                >
                  {option.label}
                  <span>{option.count}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="public-note" role="note">
            <span className="note-icon" aria-hidden="true">
              i
            </span>
            <p>
              <strong>이 컬렉션은 읽기 전용입니다.</strong>
              콘텐츠 추가와 수정은 저장소 운영자만 할 수 있습니다.
            </p>
          </div>

          <p className="results-summary" aria-live="polite">
            {hasSearch ? `검색 결과 ${filteredLenses.length}개` : `${filteredLenses.length}개 렌즈 표시 중`}
          </p>

          {filteredLenses.length > 0 ? (
            <div className="lens-grid">
              {filteredLenses.map((lens) => {
                const published = isPublished(lens);
                const preview = lens.content.trim() || lens.notes.trim();
                const title = lens.title.trim() || `렌즈 ${lens.number}`;

                return (
                  <article
                    key={lens.number}
                    className={`lens-card ${published ? "is-published" : "is-upcoming"}`}
                  >
                    <div className="card-topline">
                      <span className="lens-number">#{numberLabel(lens.number)}</span>
                      <span className="card-state">
                        {published ? "PUBLISHED" : "UPCOMING"}
                      </span>
                    </div>

                    <div className="card-body">
                      <h3>{published ? title : "준비 중인 렌즈"}</h3>
                      <p>
                        {published
                          ? preview || "키워드로 구성된 렌즈입니다."
                          : "운영자가 새로운 관점을 준비하고 있습니다."}
                      </p>
                    </div>

                    {published && lens.keywords.length > 0 ? (
                      <ul className="keyword-list" aria-label="키워드">
                        {lens.keywords.slice(0, 3).map((keyword) => (
                          <li key={keyword}>#{keyword}</li>
                        ))}
                        {lens.keywords.length > 3 ? (
                          <li>+{lens.keywords.length - 3}</li>
                        ) : null}
                      </ul>
                    ) : (
                      <div className="keyword-placeholder" aria-hidden="true" />
                    )}

                    <button
                      type="button"
                      className="card-action"
                      disabled={!published}
                      onClick={(event) => openLens(lens.number, event.currentTarget)}
                      aria-label={published ? `${lens.number}번 렌즈 내용 읽기` : undefined}
                    >
                      {published ? "내용 읽기" : "공개 준비 중"}
                      {published ? <span aria-hidden="true">↗</span> : null}
                    </button>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="empty-results">
              <span aria-hidden="true">⌕</span>
              <h3>{hasSearch ? "일치하는 렌즈가 없습니다" : "표시할 렌즈가 없습니다"}</h3>
              <p>
                {hasSearch
                  ? "다른 번호나 키워드로 다시 검색해 보세요."
                  : "다른 공개 상태 필터를 선택해 보세요."}
              </p>
            </div>
          )}
        </section>
      </main>

      <footer className="site-footer">
        <span>PUBLIC READ-ONLY COLLECTION</span>
        <p>콘텐츠 수정 권한은 저장소 운영자에게만 있습니다.</p>
      </footer>
      </div>

      {selectedLens ? (
        <div
          className="dialog-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeLens();
          }}
        >
          <section
            ref={dialogRef}
            className="lens-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="dialog-title"
          >
            <div className="dialog-header">
              <div>
                <p>PUBLIC LENS · #{numberLabel(selectedLens.number)}</p>
                <h2 id="dialog-title">
                  {selectedLens.title.trim() || `렌즈 ${selectedLens.number}`}
                </h2>
              </div>
              <button
                ref={closeButtonRef}
                type="button"
                className="dialog-close"
                onClick={closeLens}
                aria-label="렌즈 상세 닫기"
              >
                ×
              </button>
            </div>

            <div className="dialog-content">
              {selectedLens.content.trim() ? (
                <section className="detail-section">
                  <h3>렌즈 내용</h3>
                  <p className="lens-copy">{selectedLens.content}</p>
                </section>
              ) : null}

              {selectedLens.keywords.length > 0 ? (
                <section className="detail-section">
                  <h3>키워드</h3>
                  <ul className="detail-keywords">
                    {selectedLens.keywords.map((keyword) => (
                      <li key={keyword}>#{keyword}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {selectedLens.notes.trim() ? (
                <section className="detail-section detail-notes">
                  <h3>보충 메모</h3>
                  <p className="lens-copy">{selectedLens.notes}</p>
                </section>
              ) : null}
            </div>

            <div className="dialog-footer">
              <span>READ ONLY</span>
              <button type="button" onClick={closeLens}>
                닫기
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
