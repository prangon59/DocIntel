import { CrossVerifyView } from "@/components/crossverify/crossverify-view";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cross-Document Verification | AI Document Intelligence",
  description: "Cross-document financial reconciliation and discrepancy analysis.",
};

export default function CrossVerifyPage() {
  return <CrossVerifyView />;
}
