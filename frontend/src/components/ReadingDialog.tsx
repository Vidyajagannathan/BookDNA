import { FormEvent, useEffect, useRef, useState } from "react";
import { Heart, X } from "lucide-react";
import type { Book, LibraryStatus } from "../types";
import { readReadingDraft, writeReadingDraft } from "../lib/readingDraft";

const statuses: [LibraryStatus, string][] = [
  ["WANT_TO_READ", "Want to read"],
  ["CURRENTLY_READING", "Reading"],
  ["READ", "Read"],
  ["DNF", "Did not finish"],
];
type ReadingDraft = {
  status: LibraryStatus;
  rating: string;
  favourite: boolean;
  reason: string;
  note: string;
  recommend: boolean;
};

export function ReadingDialog({
  book,
  onClose,
  onSave,
  onRemove,
  pending,
  error,
}: {
  book: Book;
  onClose: () => void;
  onSave: (values: {
    status: LibraryStatus;
    rating?: number;
    favourite: boolean;
    dnf_reason?: string;
    private_note?: string;
    recommend: boolean;
  }) => void;
  onRemove?: () => void;
  pending: boolean;
  error?: string;
}) {
  const [draft] = useState<ReadingDraft | undefined>(() =>
    readReadingDraft<ReadingDraft>(book.id),
  );
  const [status, setStatus] = useState<LibraryStatus>(
    draft?.status || book.status || "WANT_TO_READ",
  );
  const [rating, setRating] = useState(
    draft?.rating ?? book.rating?.toString() ?? "",
  );
  const [favourite, setFavourite] = useState(
    draft?.favourite ?? Boolean(book.favourite),
  );
  const [reason, setReason] = useState(draft?.reason ?? book.dnf_reason ?? "");
  const [note, setNote] = useState(draft?.note ?? book.private_note ?? "");
  const [recommend, setRecommend] = useState(draft?.recommend ?? true);
  const numericRating = rating ? Number(rating) : undefined;
  const dialog = useRef<HTMLFormElement>(null);
  const mounted = useRef(false);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.focus();
    return () => previous?.focus();
  }, []);
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true;
      return;
    }
    writeReadingDraft(book.id, {
      status,
      rating,
      favourite,
      reason,
      note,
      recommend,
    } satisfies ReadingDraft);
  }, [book.id, status, rating, favourite, reason, note, recommend]);
  const keyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Escape" && !pending) {
      event.preventDefault();
      onClose();
    }
    if (event.key === "Tab" && dialog.current) {
      const focusable = [
        ...dialog.current.querySelectorAll<HTMLElement>(
          "button:not(:disabled),select:not(:disabled),textarea:not(:disabled),input:not(:disabled),a[href]",
        ),
      ];
      if (!focusable.length) return;
      const first = focusable[0],
        last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSave({
      status,
      rating: numericRating,
      favourite,
      dnf_reason: status === "DNF" ? reason : undefined,
      private_note: note,
      recommend:
        status === "READ" &&
        Boolean(numericRating && numericRating >= 3.5) &&
        recommend,
    });
  };
  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={(event) =>
        event.target === event.currentTarget && !pending && onClose()
      }
    >
      <form
        ref={dialog}
        tabIndex={-1}
        className="reading-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="reading-title"
        aria-describedby={error ? "reading-error" : undefined}
        onKeyDown={keyDown}
        onSubmit={submit}
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
        <span className="eyebrow">Update your library</span>
        <h2 id="reading-title">{book.title}</h2>
        <p>{book.author}</p>
        {draft && (
          <p className="draft-restored" role="status">
            Unsaved changes were restored on this device.
          </p>
        )}
        <fieldset disabled={pending}>
          <legend>Reading status</legend>
          <div className="status-options">
            {statuses.map(([value, label]) => (
              <button
                type="button"
                key={value}
                className={status === value ? "active" : ""}
                onClick={() => setStatus(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </fieldset>
        <label>
          Rating (optional)
          <select
            disabled={pending}
            value={rating}
            onChange={(event) => setRating(event.target.value)}
          >
            <option value="">Not rated</option>
            {Array.from({ length: 10 }, (_, index) => (index + 1) / 2).map(
              (value) => (
                <option key={value} value={value}>
                  {value} stars
                </option>
              ),
            )}
          </select>
        </label>
        <button
          disabled={pending}
          type="button"
          className={`favourite-toggle ${favourite ? "active" : ""}`}
          onClick={() => setFavourite((value) => !value)}
        >
          <Heart size={18} fill={favourite ? "currentColor" : "none"} />
          {favourite ? "Favourite" : "Add to favourites"}
        </button>
        {status === "READ" && numericRating && numericRating >= 3.5 && (
          <label className="confirm-check">
            <input
              disabled={pending}
              type="checkbox"
              checked={recommend}
              onChange={(event) => setRecommend(event.target.checked)}
            />{" "}
            Show recommendations with similar catalog themes after saving.
          </label>
        )}
        {status === "DNF" && (
          <label>
            Why didn’t you finish? <span>(optional)</span>
            <textarea
              disabled={pending}
              maxLength={500}
              rows={3}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="For example: the pacing was too slow."
            />
            <small>{reason.length}/500</small>
          </label>
        )}
        <label>
          My private notes <span>(optional)</span>
          <textarea
            disabled={pending}
            maxLength={2000}
            rows={5}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Add thoughts, quotes, reminders, or anything you want to remember…"
          />
          <small>Only visible in your account · {note.length}/2000</small>
        </label>
        <div className="dialog-actions">
          {error && (
            <p className="error" id="reading-error" role="alert">
              {error} Your draft remains on this device.
            </p>
          )}
          <button className="button primary" disabled={pending}>
            {pending ? "Saving…" : "Save to library"}
          </button>
          {onRemove && (
            <button
              disabled={pending}
              type="button"
              className="remove-book"
              onClick={onRemove}
            >
              Remove from Library
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
