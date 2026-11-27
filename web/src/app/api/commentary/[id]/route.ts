import type { NextRequest } from "next/server";
import { getVerseCommentary } from "@/lib/commentary";
import { refLabel } from "@/lib/bible";

export async function GET(_req: NextRequest, ctx: RouteContext<"/api/commentary/[id]">) {
  const { id } = await ctx.params;
  const n = Number(id);
  if (!Number.isInteger(n) || n <= 0) return Response.json({ error: "bad id" }, { status: 400 });
  const groups = getVerseCommentary(n);
  return Response.json({ label: refLabel(n, n), groups });
}
