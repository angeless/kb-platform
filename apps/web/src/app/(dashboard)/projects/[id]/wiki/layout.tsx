"use client";

import { useParams } from "next/navigation";
import { WikiLayout } from "@/components/wiki-layout";
import { WikiScrollProvider } from "@/components/wiki-scroll-context";

export default function WikiRouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const projectId = params.id as string;

  return (
    <WikiScrollProvider>
      <WikiLayout projectId={projectId}>{children}</WikiLayout>
    </WikiScrollProvider>
  );
}
