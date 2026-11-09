import { SearchView } from "@/components/search/search-view";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Search Documents | AI Document Intelligence",
  description: "Keyword, semantic, and hybrid search across processed invoices and spreadsheets.",
};

export default function SearchPage() {
  return <SearchView />;
}
