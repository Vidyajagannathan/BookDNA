export type Trait = { id: string; name: string; category: string; score: number; confidence: number }
export type Book = { id: string; title: string; author: string; year?: number; cover_url?: string; subjects?: string[]; edition_count?: number; isbn?: string[]; source?: string; status?: LibraryStatus; rating?: number; favourite?: boolean }
export type BookSearch = { books: Book[]; page: number; limit: number; total: number; has_more: boolean; source: string }
export type BookCollection = { id: string; name: string; query: string }
export type LibraryStatus = 'READ' | 'CURRENTLY_READING' | 'WANT_TO_READ' | 'DNF'
export type User = { id: string; username: string }
