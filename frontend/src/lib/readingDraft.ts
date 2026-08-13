const draftKey = (bookId: string) => `bookdna-reading-draft:${bookId}`;
export const clearReadingDraft = (bookId: string) =>
  localStorage.removeItem(draftKey(bookId));
export const readReadingDraft = <T>(bookId: string): T | undefined => {
  try {
    return (
      JSON.parse(localStorage.getItem(draftKey(bookId)) || "null") || undefined
    );
  } catch {
    return undefined;
  }
};
export const writeReadingDraft = (bookId: string, draft: unknown) =>
  localStorage.setItem(draftKey(bookId), JSON.stringify(draft));
