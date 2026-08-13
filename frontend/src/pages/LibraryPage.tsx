import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { BookCard } from "../components/BookCard";
import { ReadingDialog } from "../components/ReadingDialog";
import { clearReadingDraft } from "../lib/readingDraft";
import { RecommendationsDialog } from "../components/RecommendationsDialog";
import type { Book, LibraryStatus } from "../types";

const filters: [LibraryStatus | "ALL", string][] = [
  ["ALL", "All"],
  ["CURRENTLY_READING", "Reading"],
  ["READ", "Read"],
  ["WANT_TO_READ", "Want to read"],
  ["DNF", "DNF"],
];

export function LibraryPage() {
  const [filter, setFilter] = useState<LibraryStatus | "ALL">("ALL");
  const [editing, setEditing] = useState<Book>();
  const [recommendations, setRecommendations] = useState<string>();
  const [saveError, setSaveError] = useState("");
  const [saveNotice, setSaveNotice] = useState("");
  const queryClient = useQueryClient();
  const session = useQuery({
    queryKey: ["auth", "me"],
    queryFn: api.me,
    retry: false,
  });
  const library = useQuery({
    queryKey: ["library"],
    queryFn: api.library,
    retry: false,
    enabled: Boolean(session.data),
  });
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["library"] });
    void queryClient.invalidateQueries({ queryKey: ["dna"] });
  };
  const update = useMutation({
    mutationFn: ({
      book,
      status,
      rating,
      favourite,
      reason,
      note,
      recommend,
    }: {
      book: Book;
      status: LibraryStatus;
      rating?: number;
      favourite: boolean;
      reason?: string;
      note?: string;
      recommend: boolean;
    }) =>
      queryClient
        .fetchQuery({ queryKey: ["auth", "me"], queryFn: api.me, staleTime: 0 })
        .then(() =>
          api.updateBook(book, status, rating, favourite, reason, note),
        )
        .then((saved) => ({ saved, recommend })),
    onSuccess: ({ saved, recommend }, variables) => {
      clearReadingDraft(variables.book.id);
      setSaveError("");
      setSaveNotice(`Saved “${variables.book.title}”.`);
      window.setTimeout(() => setSaveNotice(""), 4000);
      setEditing(undefined);
      refresh();
      if (recommend) setRecommendations(saved.id);
    },
    onError: (error) =>
      setSaveError(
        error.message || "The book could not be saved. Please try again.",
      ),
    retry: false,
  });
  const remove = useMutation({
    mutationFn: (bookId: string) => api.removeBook(bookId),
    onSuccess: () => {
      setEditing(undefined);
      refresh();
    },
  });
  if (session.isPending)
    return (
      <section className="page">
        <div className="empty">Loading your library…</div>
      </section>
    );
  if (!session.data)
    return (
      <section className="page">
        <div className="empty">
          <BookOpen />
          <h2>Sign in to open your library</h2>
          <p>
            Your saved books, reading statuses, ratings and private notes live
            here.
          </p>
          <Link className="button primary" to="/login?next=/library">
            Sign in
          </Link>
        </div>
      </section>
    );
  const all = library.data?.books || [];
  const books =
    filter === "ALL" ? all : all.filter((book) => book.status === filter);
  return (
    <section className="page">
      {saveNotice && (
        <div className="save-toast" role="status">
          {saveNotice}
        </div>
      )}
      <div className="page-heading row">
        <div>
          <span className="eyebrow">Your reading life</span>
          <h1>The library</h1>
        </div>
        <strong className="big-count">
          {all.length}
          <small>books</small>
        </strong>
      </div>
      <div className="filter-tabs">
        {filters.map(([value, label]) => (
          <button
            key={value}
            className={filter === value ? "active" : ""}
            onClick={() => setFilter(value)}
          >
            {label}{" "}
            <small>
              {value === "ALL"
                ? all.length
                : all.filter((book) => book.status === value).length}
            </small>
          </button>
        ))}
      </div>
      {library.isPending ? (
        <div className="empty">Loading your books…</div>
      ) : books.length ? (
        <div className="book-grid">
          {books.map((book) => (
            <div key={book.id}>
              <BookCard book={book} onEdit={setEditing} />
              {book.status === "READ" && book.rating && book.rating >= 3.5 && (
                <button
                  className="similar-link"
                  onClick={() => setRecommendations(book.id)}
                >
                  Find similar books
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="empty">
          <BookOpen />
          <h2>
            {filter === "ALL"
              ? "No books here—yet."
              : `No books marked ${filters.find((item) => item[0] === filter)?.[1].toLowerCase()}.`}
          </h2>
          <p>
            {filter === "ALL"
              ? "The first book is the first strand of your BookDNA."
              : "Choose another shelf or update a book’s reading status."}
          </p>
        </div>
      )}
      {editing && (
        <ReadingDialog
          book={editing}
          pending={update.isPending || remove.isPending}
          error={saveError}
          onClose={() => {
            setEditing(undefined);
            setSaveError("");
          }}
          onSave={(values) =>
            update.mutate({
              book: editing,
              status: values.status,
              rating: values.rating,
              favourite: values.favourite,
              reason: values.dnf_reason,
              note: values.private_note,
              recommend: values.recommend,
            })
          }
          onRemove={() => {
            const affects =
              editing.status === "READ" ||
              editing.status === "CURRENTLY_READING" ||
              editing.status === "DNF";
            const warning = affects
              ? "Removing this book will delete its rating, favourite and notes, and recalculate your BookDNA. Continue?"
              : "Remove this book from your Library? It does not currently add positive BookDNA evidence.";
            if (window.confirm(warning)) remove.mutate(editing.id);
          }}
        />
      )}
      {recommendations && (
        <RecommendationsDialog
          bookId={recommendations}
          onClose={() => setRecommendations(undefined)}
        />
      )}
    </section>
  );
}
