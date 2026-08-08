import { Bookmark, Heart } from 'lucide-react'
import type { Book } from '../types'

export function BookCard({ book, onAdd }: { book: Book; onAdd?: (book: Book) => void }) {
  return <article className="book-card"><div className="cover-wrap">{book.cover_url ? <img src={book.cover_url} alt={`Cover of ${book.title}`} loading="lazy"/> : <div className="cover-placeholder"><span>{book.title}</span></div>}<button aria-label={`Save ${book.title}`} onClick={() => onAdd?.(book)}><Bookmark size={17}/></button></div><div className="book-info"><h3>{book.title}</h3><p>{book.author}</p><div className="book-meta"><span>{book.year || '—'}</span><span><Heart size={13}/> {book.rating || 'New'}</span></div></div></article>
}

