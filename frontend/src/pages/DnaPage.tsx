import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { BookCheck, CircleAlert, Dna, RefreshCw } from "lucide-react";
import { DnaVisual } from "../components/DnaVisual";
import { api } from "../lib/api";
import type { CompletedClassification } from "../types";

const stateLabel = (book: CompletedClassification) =>
  book.state === "partial_collection" ? "Collection — partially included" :
  book.state === "duplicate_excluded" ? "Excluded — duplicate evidence" :
  book.included ? "Included" : "Needs classification";

export function DnaPage() {
  const [showBooks, setShowBooks] = useState(false);
  const session = useQuery({ queryKey: ["auth", "me"], queryFn: api.me, retry: false });
  const dna = useQuery({ queryKey: ["dna"], queryFn: api.dna, enabled: Boolean(session.data), retry: 1 });

  if (session.isPending || (session.data && dna.isPending))
    return <section className="page"><div className="empty"><RefreshCw className="spin"/><h2>Reading your library…</h2><p>We are classifying each completed book and rebuilding your portrait.</p></div></section>;
  if (!session.data)
    return <section className="page"><div className="empty"><Dna/><h1>Sign in to reveal your BookDNA</h1><p>Your DNA is private and forms from books you read, rate and favourite.</p><Link className="button primary" to="/login?next=/dna">Sign in</Link> <Link className="button" to="/register?next=/dna">Create account</Link></div></section>;
  if (dna.isError)
    return <section className="page"><div className="empty"><CircleAlert/><h2>We couldn’t build your BookDNA</h2><p>{dna.error.message} Your library is safe.</p><button className="button primary" onClick={() => void dna.refetch()}>Try again</button></div></section>;
  if (!dna.data)
    return <section className="page"><div className="empty"><CircleAlert/><h2>Your BookDNA is unavailable</h2><button className="button primary" onClick={() => void dna.refetch()}>Try again</button></div></section>;

  const profile = dna.data;
  const classifications = profile.completed_classifications;
  const noLibrary = profile.total_books === 0;
  const noCompleted = profile.completed_books === 0;
  const noClassified = profile.completed_books > 0 && profile.books_shaping === 0;

  return <section className="page dna-page">
    <div className="page-heading"><span className="eyebrow">The pattern behind your pages</span><h1>Your Book<span>DNA</span></h1><p>A transparent portrait based on the reading choices in your Library.</p></div>
    {noLibrary && <div className="dna-guidance"><h2>Your portrait starts with a book</h2><p>Add books to your Library, then mark completed books as Read. Ratings and favourites make the signals more precise.</p><Link className="button primary" to="/discover">Find a book</Link></div>}
    {noCompleted && !noLibrary && <div className="dna-guidance"><h2>No completed books yet</h2><p>Want-to-read books do not define you. Mark a book Read when you finish it; currently-reading books contribute only a small early signal.</p><Link className="button" to="/library">Update your library</Link></div>}
    {noClassified && <div className="dna-guidance warning"><h2>We need better details for these books</h2><p>Your completed books are safe, but their catalogue subjects are not detailed enough to form traits yet. Open the list below to see exactly which books need classification.</p></div>}
    <DnaVisual traits={profile.traits} profileConfidence={profile.profile_confidence} confidenceLabel={profile.confidence_label}/>
    <div className="completion-summary"><strong>{profile.completed_books} of {profile.total_books} books read — {profile.completion_rate}%</strong><span>Completion rate is separate from profile confidence.</span></div>
    <div className="dna-explain"><button onClick={() => setShowBooks(value => !value)} aria-expanded={showBooks}><strong>{profile.books_shaping}</strong><span>books shaping your DNA</span><small>{showBooks ? "Hide evidence" : "See exactly what counts"}</small></button><article><strong>{profile.active_traits}</strong><span>supported traits</span></article><article><strong>{profile.unclassified_books}</strong><span>books needing details</span></article></div>
    {showBooks && <section className="classification-panel"><div><h2>How each completed book is used</h2><p>Read books contribute fully. Ratings and favourites adjust their strength. Collections are de-duplicated, and books without reliable metadata are clearly identified.</p></div>{classifications.length ? <div className="classification-list">{classifications.map(book => <article key={book.id} className={book.state.replaceAll("_", "-")}>{book.included ? <BookCheck/> : <CircleAlert/>}<div><h3>{book.title}</h3><p>{book.author || "Unknown author"} · {book.reading_type === "academic" ? "Academic reading" : "Recreational reading"}{book.format_type === "collection" ? " · Collection" : ""}</p><span>{stateLabel(book)}</span><small>{book.reason}{book.series_name ? ` Series: ${book.series_name}.` : ""}{book.traits.length ? ` Traits: ${book.traits.join(", ")}.` : ""}{book.duplicate_titles.length ? ` Overlap removed: ${book.duplicate_titles.join(", ")}.` : ""}</small></div></article>)}</div> : <p>No completed books yet.</p>}</section>}
    <p className="metric-explanation"><b>Preference strength</b> shows the share and consistency of supporting reading evidence. <b>Profile confidence</b> grows with more classified books, ratings and repeated support. One book is always treated as an early clue.</p>
  </section>;
}
