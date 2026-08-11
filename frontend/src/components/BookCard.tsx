import { Bookmark, Check, Heart } from 'lucide-react'
import type { Book } from '../types'

export function BookCard({ book, onAdd, saved = false }: { book: Book; onAdd?: (book: Book) => void; saved?: boolean }) {
  return <article className="book-card"><div className="cover-wrap">{book.cover_url ? <img src={book.cover_url} alt={`Cover of ${book.title}`} loading="lazy"/> : <div className="cover-placeholder"><span>{book.title}</span></div>}<button className={saved ? 'saved' : ''} disabled={saved} aria-label={saved ? `${book.title} saved` : `Save ${book.title}`} onClick={() => onAdd?.(book)}>{saved ? <Check size={17}/> : <Bookmark size={17}/>}</button></div><div className="book-info"><h3>{book.title}</h3><p>{book.author}</p><div className="book-meta"><span>{book.year || '—'}</span><span>{book.edition_count ? `${book.edition_count} editions` : <><Heart size={13}/> {book.rating || 'New'}</>}</span></div></div></article>
}
