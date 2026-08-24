import type {
  AdminStats,
  Book,
  BookCollection,
  BookSearch,
  DnaProfile,
  LibraryStatus,
  Profile,
  RecommendationBook,
  User,
  DnaDiagnostic,
} from "../types";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...init?.headers },
      ...init,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError")
      throw new ApiError(
        "The request took too long. Your draft is safe—please try again.",
        408,
      );
    throw error;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail || "Something went wrong", response.status);
  }
  return response.json();
}

export const api = {
  me: () => request<User>("/auth/me"),
  login: (identifier: string, password: string, remember = true) =>
    request<User>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password, remember }),
    }),
  register: (
    username: string,
    email: string,
    password: string,
    remember = true,
  ) =>
    request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password, remember }),
    }),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  logoutAll: () =>
    request<{ ok: boolean }>("/auth/logout-all", { method: "POST" }),
  deleteAccount: (password: string) =>
    request<{ ok: boolean }>("/auth/account", {
      method: "DELETE",
      body: JSON.stringify({ password }),
    }),
  profile: () => request<Profile>("/auth/profile"),
  updateProfile: (
    profile: Pick<
      Profile,
      "display_name" | "timezone" | "date_format" | "language" | "avatar"
    >,
  ) =>
    request<Profile>("/auth/profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    }),
  changePassword: (current_password: string, new_password: string) =>
    request<{ ok: boolean }>("/auth/password", {
      method: "PUT",
      body: JSON.stringify({ current_password, new_password }),
    }),
  search: (
    q: string,
    page = 1,
    limit = 24,
    signal?: AbortSignal,
    sort = "relevance",
  ) =>
    request<BookSearch>(
      `/books/search?q=${encodeURIComponent(q)}&page=${page}&limit=${limit}&sort=${encodeURIComponent(sort)}`,
      { signal },
    ),
  book: (bookId: string) =>
    request<{ book: Book; editions: unknown[] }>(
      `/books/${encodeURIComponent(bookId)}`,
    ),
  collections: () =>
    request<{ collections: BookCollection[] }>("/books/collections"),
  library: () => request<{ books: Book[] }>("/library"),
  updateBook: (
    book: Book,
    status: LibraryStatus,
    rating?: number,
    favourite = false,
    dnf_reason?: string,
    private_note?: string,
  ) =>
    request<Book>(`/library/${encodeURIComponent(book.id)}`, {
      method: "PUT",
      body: JSON.stringify({
        book,
        status,
        rating,
        favourite,
        dnf_reason,
        private_note,
      }),
      signal: AbortSignal.timeout(15_000),
    }),
  removeBook: (bookId: string) =>
    request<{ ok: boolean }>(`/library/${encodeURIComponent(bookId)}`, {
      method: "DELETE",
    }),
  dna: () => request<DnaProfile>("/dna/me"),
  recommendations: (bookId: string) =>
    request<{
      source: Book;
      similar: RecommendationBook[];
      by_author: RecommendationBook[];
      basis: string;
    }>(`/recommendations/${encodeURIComponent(bookId)}`),
  adminStats: () => request<AdminStats>("/admin/stats"),
  dnaDiagnostic: (email:string) => request<DnaDiagnostic>(`/admin/dna-diagnostic?email=${encodeURIComponent(email)}`),
};
