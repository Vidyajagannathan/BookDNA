import { FormEvent, useEffect, useState } from "react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { LoaderCircle, Search, Sparkles } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { BookCard } from "../components/BookCard";
import { BookDetailsDialog } from "../components/BookDetailsDialog";
import { ReadingDialog } from "../components/ReadingDialog";
import { clearReadingDraft } from "../lib/readingDraft";
import type { Book, LibraryStatus } from "../types";

const pendingBookKey = "bookdna-pending-book";
const standardSortOptions = [
  ["relevance", "Relevance"],
  ["popular", "Most popular"],
  ["newest", "Newest first"],
  ["oldest", "Oldest first"],
  ["title_asc", "Title A–Z"],
  ["title_desc", "Title Z–A"],
] as const;
const booktokSortOptions = [
  ["featured", "Featured"],
  ["popular", "Most popular"],
  ["newest", "Newest first"],
  ["oldest", "Oldest first"],
  ["title_asc", "Title A–Z"],
  ["title_desc", "Title Z–A"],
] as const;

export function Discover() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const initialQuery = params.get("q")?.trim() || "subject:classics";
  const initialHeading =
    params.get("label")?.trim() ||
    (params.get("q") ? `Results for “${params.get("q")}”` : "Classics");
  const initialSort =
    params.get("sort") ||
    (initialQuery.startsWith("booktok:")
      ? "featured"
      : initialQuery.startsWith("subject:")
        ? "popular"
        : "relevance");
  const [q, setQ] = useState(params.get("q") || "");
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  const [heading, setHeading] = useState(initialHeading);
  const [sort, setSort] = useState(initialSort);
  const [editing, setEditing] = useState<Book>();
  const [viewing, setViewing] = useState<Book>();
  const [saveError, setSaveError] = useState("");
  const [saveNotice, setSaveNotice] = useState("");
  const [slow, setSlow] = useState(false);
  const queryClient = useQueryClient();
  const isBookTok = activeQuery.startsWith("booktok:");
  const sortOptions = isBookTok ? booktokSortOptions : standardSortOptions;
  const session = useQuery({
    queryKey: ["auth", "me"],
    queryFn: api.me,
    retry: false,
  });
  const collections = useQuery({
    queryKey: ["book-collections"],
    queryFn: api.collections,
  });
  const library = useQuery({
    queryKey: ["library"],
    queryFn: api.library,
    retry: false,
    enabled: Boolean(session.data),
  });
  const search = useInfiniteQuery({
    queryKey: ["book-search", activeQuery, sort],
    queryFn: ({ pageParam, signal }) =>
      api.search(activeQuery, pageParam, 24, signal, sort),
    initialPageParam: 1,
    getNextPageParam: (page) => (page.has_more ? page.page + 1 : undefined),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
  useEffect(() => {
    setSlow(false);
    if (!search.isFetching) return;
    const timer = window.setTimeout(() => setSlow(true), 5000);
    return () => window.clearTimeout(timer);
  }, [search.isFetching, activeQuery]);
  useEffect(() => {
    if (!session.data || params.get("save") !== "pending") return;
    try {
      const raw = sessionStorage.getItem(pendingBookKey);
      if (raw) {
        setEditing(JSON.parse(raw) as Book);
        sessionStorage.removeItem(pendingBookKey);
      }
    } catch {
      sessionStorage.removeItem(pendingBookKey);
    }
    const next = new URLSearchParams(params);
    next.delete("save");
    setParams(next, { replace: true });
  }, [session.data, params, setParams]);
  const requireSession = (book: Book) => {
    setViewing(undefined);
    setSaveError("");
    if (session.data) {
      setEditing(book);
      return;
    }
    sessionStorage.setItem(pendingBookKey, JSON.stringify(book));
    const returnTo = new URLSearchParams(params);
    returnTo.set("save", "pending");
    navigate(`/login?next=${encodeURIComponent(`/discover?${returnTo}`)}`);
  };
  const save = useMutation({
    mutationFn: ({
      book,
      values,
    }: {
      book: Book;
      values: [
        LibraryStatus,
        number | undefined,
        boolean,
        string | undefined,
        string | undefined,
      ];
    }) =>
      queryClient
        .fetchQuery({ queryKey: ["auth", "me"], queryFn: api.me, staleTime: 0 })
        .then(() => api.updateBook(book, ...values)),
    onSuccess: (_saved, variables) => {
      clearReadingDraft(variables.book.id);
      setEditing(undefined);
      setSaveError("");
      setSaveNotice(`Saved “${variables.book.title}” to your library.`);
      window.setTimeout(() => setSaveNotice(""), 4000);
      sessionStorage.removeItem(pendingBookKey);
      void queryClient.invalidateQueries({ queryKey: ["library"] });
      void queryClient.invalidateQueries({ queryKey: ["dna"] });
    },
    onError: (error, variables) => {
      if (error instanceof ApiError && error.status === 401) {
        sessionStorage.setItem(pendingBookKey, JSON.stringify(variables.book));
        setEditing(undefined);
        const returnTo = new URLSearchParams(params);
        returnTo.set("save", "pending");
        navigate(`/login?next=${encodeURIComponent(`/discover?${returnTo}`)}`);
        return;
      }
      setSaveError(
        error.message || "The book could not be saved. Please try again.",
      );
    },
    retry: false,
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const next = q.trim();
    if (next.length >= 2) {
      setActiveQuery(next);
      setHeading(`Results for “${next}”`);
      setSort("relevance");
      setParams({ q: next, sort: "relevance" });
    }
  };
  const choose = (name: string, query: string) => {
    const nextSort = query.startsWith("booktok:") ? "featured" : "popular";
    setActiveQuery(query);
    setHeading(name);
    setQ("");
    setSort(nextSort);
    setParams({ q: query, label: name, sort: nextSort });
  };
  const chooseBookTokCategory = (category: string) => {
    const query = `booktok:${category.toLowerCase().replaceAll(" ", "-")}`;
    setActiveQuery(query);
    setHeading(category === "All" ? "BookTok" : `BookTok · ${category}`);
    setSort("featured");
    setParams({
      q: query,
      label: category === "All" ? "BookTok" : `BookTok · ${category}`,
      sort: "featured",
    });
  };
  const changeSort = (next: string) => {
    setSort(next);
    const updated = new URLSearchParams(params);
    updated.set("sort", next);
    setParams(updated);
  };
  const books = search.data?.pages.flatMap((page) => page.books) || [];
  const saved = new Map(
    (library.data?.books || []).map((book) => [book.id, book]),
  );
  const firstPage = search.data?.pages[0];
  const total = firstPage?.total;
  const collection = firstPage?.collection;
  return (
    <section className="page discover">
      {saveNotice && (
        <div className="save-toast" role="status">
          {saveNotice}
        </div>
      )}
      <div className="page-heading">
        <span className="eyebrow">A global catalog, your next signal</span>
        <h1>
          Find a book that
          <br />
          <em>changes the pattern.</em>
        </h1>
        <p>
          Search titles, authors, subjects, or ISBNs across millions of
          bibliographic records.
        </p>
      </div>
      <form className="searchbar" onSubmit={submit}>
        <Search />
        <input
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="Search by title, author, subject, or ISBN…"
          aria-label="Search books"
        />
        <button>Search</button>
      </form>
      <div className="collection-scroll">
        <div className="collection-tabs" aria-label="Browse collections">
          {collections.data?.collections.map((item) => (
            <button
              key={item.id}
              className={
                activeQuery === item.query ||
                (item.id === "booktok" && isBookTok)
                  ? "active"
                  : ""
              }
              onClick={() => choose(item.name, item.query)}
            >
              {item.name}
            </button>
          ))}
        </div>
      </div>
      <p className="collection-hint">
        Swipe or scroll for more categories <span aria-hidden="true">→</span>
      </p>
      {isBookTok && collection && (
        <aside className="booktok-intro">
          <div>
            <span className="eyebrow">
              Community favourites · curated{" "}
              {new Date(`${collection.updated}T12:00:00`).toLocaleDateString(
                "en-GB",
                { day: "numeric", month: "long", year: "numeric" },
              )}
            </span>
            <p>{collection.description}</p>
          </div>
          <div
            className="booktok-categories"
            aria-label="Filter BookTok collection"
          >
            {collection.categories.map((category) => (
              <button
                key={category}
                className={
                  activeQuery ===
                  `booktok:${category.toLowerCase().replaceAll(" ", "-")}`
                    ? "active"
                    : ""
                }
                onClick={() => chooseBookTokCategory(category)}
              >
                {category}
              </button>
            ))}
          </div>
          <small>
            Editorial sources:{" "}
            {collection.sources.map((source, index) => (
              <span key={source.url}>
                {index > 0 ? " · " : ""}
                <a href={source.url} target="_blank" rel="noreferrer">
                  {source.name}
                </a>
              </span>
            ))}
          </small>
        </aside>
      )}
      <div className="results-toolbar">
        <div className="section-title">
          <div>
            <Sparkles size={17} />
            <span>{heading}</span>
          </div>
          <p>
            {search.isPending
              ? "Searching the shelves…"
              : total == null
                ? `${books.length} books found`
                : `${total.toLocaleString()} records found`}
          </p>
        </div>
        <label>
          Sort by
          <select
            value={sort}
            onChange={(event) => changeSort(event.target.value)}
          >
            {sortOptions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {sort === "popular" && (
        <p className="sort-note">
          Popularity is estimated from the number of catalog editions available.
        </p>
      )}
      {isBookTok && sort === "featured" && (
        <p className="sort-note">
          Featured order reflects the current editorial collection, not paid
          placement.
        </p>
      )}
      {search.isFetching && !search.isPending && (
        <p className="sorting-status">Updating results…</p>
      )}
      {slow && (
        <div className="slow-search">
          This search is taking longer than usual. You can keep waiting or{" "}
          <button onClick={() => search.refetch()}>try again</button>.
        </div>
      )}
      {search.error && (
        <div className="error">
          {search.error.message}{" "}
          <button onClick={() => search.refetch()}>Retry</button>.
        </div>
      )}
      <div className="book-grid">
        {books.map((book) => (
          <BookCard
            key={book.id}
            book={saved.get(book.id) || book}
            saved={saved.has(book.id)}
            onAdd={requireSession}
            onView={setViewing}
          />
        ))}
      </div>
      {!search.isPending && books.length === 0 && !search.error && (
        <div className="empty">
          <Search />
          <h2>No matching books found</h2>
          <p>
            Try a broader title, author, subject, or an ISBN without
            punctuation.
          </p>
        </div>
      )}
      {search.hasNextPage && (
        <div className="load-more">
          <button
            className="button primary"
            onClick={() => search.fetchNextPage()}
            disabled={search.isFetchingNextPage}
          >
            {search.isFetchingNextPage ? (
              <>
                <LoaderCircle className="spin" size={17} /> Loading…
              </>
            ) : (
              "Load more books"
            )}
          </button>
        </div>
      )}
      {viewing && (
        <BookDetailsDialog
          book={viewing}
          onClose={() => setViewing(undefined)}
          onSave={() => requireSession(viewing)}
        />
      )}{" "}
      {editing && (
        <ReadingDialog
          book={saved.get(editing.id) || editing}
          pending={save.isPending}
          error={saveError}
          onClose={() => {
            if (!save.isPending) {
              setEditing(undefined);
              setSaveError("");
            }
          }}
          onSave={(values) =>
            save.mutate({
              book: editing,
              values: [
                values.status,
                values.rating,
                values.favourite,
                values.dnf_reason,
                values.private_note,
              ],
            })
          }
        />
      )}
    </section>
  );
}
