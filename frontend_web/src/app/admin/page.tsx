import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { verifyAdminCookie, COOKIE_NAME } from "@/lib/admin-auth";
import { AdminDashboard } from "@/components/AdminDashboard";

function getDB() {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    if (ctx?.env?.DB) return ctx.env.DB as import("@cloudflare/workers-types").D1Database;
  } catch {}
  return null;
}

interface UserRow {
  id: string;
  name: string | null;
  email: string | null;
  id_type: string | null;
  telegram_id: string | null;
  telegram_name: string | null;
  created_at: string | null;
  plan: string | null;
  status: string | null;
  expires_at: string | null;
}

export default async function AdminPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;

  if (!(await verifyAdminCookie(token))) {
    redirect("/admin/login");
  }

  const db = getDB();
  let users: UserRow[] = [];

  if (db) {
    try {
      const { results } = await db
        .prepare(
          `SELECT u.id, u.name, u.email, u.id_type, u.telegram_id, u.telegram_name,
                  u.created_at,
                  s.plan, s.status, s.expires_at
           FROM users u
           LEFT JOIN subscriptions s ON s.user_id = u.id
           ORDER BY u.created_at DESC
           LIMIT 200`
        )
        .all<UserRow>();
      users = results;
    } catch (e) {
      console.error("[Admin] D1 fetch failed:", e);
    }
  }

  return <AdminDashboard initialUsers={users} />;
}
