import { useEffect, useRef } from "react";
import { BookMarked, BookOpen, Check, CircleSlash2, X } from "lucide-react";
import { libraryStatuses } from "../lib/libraryStatus";
import type { Book, LibraryStatus } from "../types";

const statusIcons = {
  WANT_TO_READ: BookMarked,
  CURRENTLY_READING: BookOpen,
  READ: Check,
  DNF: CircleSlash2,
};

export function QuickStatusDialog({
  book,
  onClose,
  onSelect,
  pending,
  pendingStatus,
  error,
}: {
  book: Book;
  onClose: () => void;
  onSelect: (status: LibraryStatus) => void;
  pending: boolean;
  pendingStatus?: LibraryStatus;
  error?: string;
}) {
  const dialog = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.focus();
    return () => previous?.focus();
  }, []);

  const keyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Escape" && !pending) {
      event.preventDefault();
      onClose();
    }
    if (event.key === "Tab" && dialog.current) {
      const focusable = [
        ...dialog.current.querySelectorAll<HTMLElement>(
          "button:not(:disabled)",
        ),
      ];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  };

  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={(event) =>
        event.target === event.currentTarget && !pending && onClose()
      }
    >
      <div
        ref={dialog}
        tabIndex={-1}
        className="quick-status-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="quick-status-title"
        aria-describedby="quick-status-help"
        onKeyDown={keyDown}
      >
        <button
          type="button"
          className="dialog-close"
          onClick={onClose}
          disabled={pending}
          aria-label="Close"
        >
          <X />
        </button>
        <span className="eyebrow">
          {book.status ? "Change reading status" : "Add to your library"}
        </span>
        <h2 id="quick-status-title">{book.title}</h2>
        <p className="quick-status-author">{book.author}</p>
        <p id="quick-status-help" className="quick-status-help">
          {book.status
            ? "Choose a new status. Your rating, favourite and notes will stay unchanged."
            : "Choose a reading status to save this book immediately."}
        </p>
        <div className="quick-status-options" aria-label="Reading status">
          {libraryStatuses.map(([value, label]) => {
            const Icon = statusIcons[value];
            const current = book.status === value;
            const saving = pending && pendingStatus === value;
            return (
              <button
                type="button"
                key={value}
                className={`${current ? "active" : ""} ${saving ? "saving" : ""}`}
                disabled={pending}
                aria-current={current ? "true" : undefined}
                onClick={() => (current ? onClose() : onSelect(value))}
              >
                <Icon size={19} />
                <span>{label}</span>
                {(current || saving) && (
                  <small>{saving ? "Saving…" : "Current"}</small>
                )}
              </button>
            );
          })}
        </div>
        {error && (
          <p className="error quick-status-error" role="alert">
            {error}
          </p>
        )}
        <p className="quick-status-footnote">
          Ratings, favourites, private notes and similar-book suggestions are
          available from the pencil icon in your Library.
        </p>
      </div>
    </div>
  );
}
