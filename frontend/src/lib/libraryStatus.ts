import type { LibraryStatus } from "../types";

export const libraryStatuses: [LibraryStatus, string][] = [
  ["WANT_TO_READ", "Want to read"],
  ["CURRENTLY_READING", "Reading"],
  ["READ", "Read"],
  ["DNF", "Did not finish"],
];

export function libraryStatusLabel(status: LibraryStatus) {
  return libraryStatuses.find(([value]) => value === status)?.[1] || status;
}
