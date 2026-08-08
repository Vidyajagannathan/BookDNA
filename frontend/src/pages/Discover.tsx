import { FormEvent, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Search, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { BookCard } from '../components/BookCard'
import type { Book } from '../types'

const starters: Book[] = [
  { id:'OL45804W', title:'The Odyssey', author:'Homer', year:-700, cover_url:'https://covers.openlibrary.org/b/id/13854144-L.jpg' },
  { id:'OL1168083W', title:'The Secret History', author:'Donna Tartt', year:1992, cover_url:'https://covers.openlibrary.org/b/id/14658380-L.jpg' },
  { id:'OL7343628W', title:'Circe', author:'Madeline Miller', year:2018, cover_url:'https://covers.openlibrary.org/b/id/10268400-L.jpg' },
  { id:'OL261270W', title:'1984', author:'George Orwell', year:1949, cover_url:'https://covers.openlibrary.org/b/id/15354106-L.jpg' },
]
export function Discover() { const [q,setQ]=useState(''); const search=useMutation({mutationFn:api.search}); const submit=(e:FormEvent)=>{e.preventDefault(); if(q.trim()) search.mutate(q.trim())}; const books=search.data?.books || starters; return <section className="page discover"><div className="page-heading"><span className="eyebrow">Discover your next signal</span><h1>Find a book that<br/><em>changes the pattern.</em></h1></div><form className="searchbar" onSubmit={submit}><Search/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search by title, author, or ISBN…" aria-label="Search books"/><button>Search</button></form><div className="section-title"><div><Sparkles size={17}/><span>{search.data ? `Results for “${q}”` : 'Books to begin with'}</span></div><p>{search.isPending ? 'Searching the shelves…' : `${books.length} books`}</p></div>{search.error && <p className="error">{search.error.message}</p>}<div className="book-grid">{books.map(book=><BookCard key={book.id} book={book} onAdd={(b)=>api.updateBook(b,'WANT_TO_READ')}/>)}</div></section> }

