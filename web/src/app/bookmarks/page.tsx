import { BookmarkList } from "@/components/BookmarkList";

export const metadata = { title: "Bookmarks and notes" };

export default function Bookmarks() {
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold tracking-tight">Bookmarks and notes</h1>
      <BookmarkList />
    </div>
  );
}
