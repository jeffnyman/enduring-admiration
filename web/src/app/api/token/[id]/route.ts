import type { NextRequest } from "next/server";
import { getWord } from "@/lib/bible";

export async function GET(_req: NextRequest, ctx: RouteContext<"/api/token/[id]">) {
  const { id } = await ctx.params;
  const n = Number(id);
  if (!Number.isInteger(n) || n <= 0) return Response.json({ error: "bad id" }, { status: 400 });
  const word = getWord(n);
  if (!word) return Response.json({ error: "not found" }, { status: 404 });
  return Response.json(word);
}
