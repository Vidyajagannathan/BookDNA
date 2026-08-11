import type { Book, BookCollection, BookSearch, LibraryStatus, Trait, User } from '../types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { credentials: 'include', headers: { 'Content-Type': 'application/json', ...init?.headers }, ...init })
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || 'Something went wrong') }
  return response.json()
}

export const api = {
  me: () => request<User>('/auth/me'),
  login: (identifier: string, password: string) => request<User>('/auth/login', { method: 'POST', body: JSON.stringify({ identifier, password }) }),
  register: (username: string, email: string, password: string) => request<User>('/auth/register', { method: 'POST', body: JSON.stringify({ username, email, password }) }),
  logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
  search: (q: string, page = 1, limit = 24) => request<BookSearch>(`/books/search?q=${encodeURIComponent(q)}&page=${page}&limit=${limit}`),
  collections: () => request<{ collections: BookCollection[] }>('/books/collections'),
  library: () => request<{ books: Book[] }>('/library'),
  updateBook: (book: Book, status: LibraryStatus, rating?: number, favourite = false) => request<Book>(`/library/${encodeURIComponent(book.id)}`, { method: 'PUT', body: JSON.stringify({ book, status, rating, favourite }) }),
  dna: () => request<{ traits: Trait[]; evidence: number }>('/dna/me'),
}
