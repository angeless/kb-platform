"use client";

import { useParams } from "next/navigation";
import { WikiLayout } from "@/components/wiki-layout";

export default function WikiRouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const projectId = params.id as string;

  return <WikiLayout projectId={projectId}>{children}</WikiLayout>;
}
