import type { NextRequest } from "next/server";
import { getCrossRefs } from "@/lib/bible";

export async function GET(_req: NextRequest, ctx: RouteContext<"/api/xrefs/[id]">) {
  const { id } = await ctx.params;
  const n = Number(id);
  if (!Number.isInteger(n) || n <= 0) return Response.json({ error: "bad id" }, { status: 400 });
  return Response.json(getCrossRefs(n));
}
