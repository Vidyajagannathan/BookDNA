import { useQuery } from '@tanstack/react-query'
import { BookOpen } from 'lucide-react'
import { api } from '../lib/api'
import { BookCard } from '../components/BookCard'
export function LibraryPage(){ const library=useQuery({queryKey:['library'],queryFn:api.library}); const books=library.data?.books||[]; return <section className="page"><div className="page-heading row"><div><span className="eyebrow">Your reading life</span><h1>The library</h1></div><strong className="big-count">{books.length}<small>books</small></strong></div><div className="filter-tabs"><button className="active">All</button><button>Reading</button><button>Read</button><button>Want to read</button><button>DNF</button></div>{library.isError?<div className="empty"><BookOpen/><h2>Your shelf is waiting</h2><p>Sign in, then add a few books from Discover to begin forming your DNA.</p></div>:books.length?<div className="book-grid">{books.map(b=><BookCard key={b.id} book={b}/>)}</div>:<div className="empty"><BookOpen/><h2>No books here—yet.</h2><p>The first book is the first strand of your BookDNA.</p></div>}</section> }

