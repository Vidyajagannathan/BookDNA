import { FormEvent, useState } from 'react'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, LoaderCircle, Search, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { BookCard } from '../components/BookCard'
import type { Book } from '../types'

export function Discover() {
  const [q, setQ] = useState('')
  const [activeQuery, setActiveQuery] = useState('subject:classics')
  const [heading, setHeading] = useState('Classics')
  const [saved, setSaved] = useState<string[]>([])
  const queryClient = useQueryClient()
  const collections = useQuery({ queryKey: ['book-collections'], queryFn: api.collections })
  const search = useInfiniteQuery({ queryKey: ['book-search', activeQuery], queryFn: ({ pageParam }) => api.search(activeQuery, pageParam, 24), initialPageParam: 1, getNextPageParam: page => page.has_more ? page.page + 1 : undefined })
  const save = useMutation({ mutationFn: (book: Book) => api.updateBook(book, 'WANT_TO_READ'), onSuccess: book => { setSaved(current => [...new Set([...current, book.id])]); void queryClient.invalidateQueries({ queryKey: ['library'] }) } })
  const submit = (event: FormEvent) => { event.preventDefault(); const next = q.trim(); if (next.length >= 2) { setActiveQuery(next); setHeading(`Results for “${next}”`) } }
  const chooseCollection = (name: string, query: string) => { setActiveQuery(query); setHeading(name); setQ('') }
  const books = search.data?.pages.flatMap(page => page.books) || []
  const total = search.data?.pages[0]?.total || 0
  return <section className="page discover">
    <div className="page-heading"><span className="eyebrow">A global catalog, your next signal</span><h1>Find a book that<br/><em>changes the pattern.</em></h1><p>Search titles, authors, subjects, or ISBNs across millions of bibliographic records.</p></div>
    <form className="searchbar" onSubmit={submit}><Search/><input value={q} onChange={event => setQ(event.target.value)} placeholder="Search by title, author, subject, or ISBN…" aria-label="Search books"/><button>Search</button></form>
    <div className="collection-tabs" aria-label="Browse collections">{collections.data?.collections.map(collection => <button key={collection.id} className={activeQuery === collection.query ? 'active' : ''} onClick={() => chooseCollection(collection.name, collection.query)}>{collection.name}</button>)}</div>
    <div className="section-title"><div><Sparkles size={17}/><span>{heading}</span></div><p>{search.isPending ? 'Searching the shelves…' : `${total.toLocaleString()} records found`}</p></div>
    {search.error && <p className="error">{search.error.message}</p>}{save.error && <p className="error">Sign in to save books to your library.</p>}
    <div className="book-grid">{books.map(book => <BookCard key={book.id} book={book} saved={saved.includes(book.id)} onAdd={item => save.mutate(item)}/>)}</div>
    {!search.isPending && books.length === 0 && !search.error && <div className="empty"><Search/><h2>No matching books found</h2><p>Try a broader title, author, subject, or an ISBN without punctuation.</p></div>}
    {search.hasNextPage && <div className="load-more"><button className="button primary" onClick={() => search.fetchNextPage()} disabled={search.isFetchingNextPage}>{search.isFetchingNextPage ? <><LoaderCircle className="spin" size={17}/> Loading…</> : 'Load more books'}</button></div>}
    {saved.length > 0 && <div className="save-toast"><Check size={16}/>{saved.length === 1 ? 'Book saved to your library' : `${saved.length} books saved`}</div>}
  </section>
}
