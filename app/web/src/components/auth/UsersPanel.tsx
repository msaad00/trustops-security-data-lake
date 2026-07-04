"use client";

import { useMemo, useState } from "react";
import { Loader2, UserCog, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
import {
  useAuthUsers,
  useAuthWhoami,
  useUpdateAuthUserMutation,
} from "@/lib/api/hooks";
import type { AuthUser } from "@/lib/api/types";
import { notify } from "@/lib/toast";

const ROLES = [
  "admin",
  "security_admin",
  "contributor",
  "auditor",
  "read_only",
] as const;

function formatWhen(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function UserRow({
  row,
  currentUserId,
  onSave,
  saving,
}: {
  row: AuthUser;
  currentUserId?: string;
  onSave: (userId: string, role: string, isActive: boolean) => void;
  saving: boolean;
}) {
  const [role, setRole] = useState(row.role);
  const [active, setActive] = useState(row.is_active);
  const dirty = role !== row.role || active !== row.is_active;
  const isSelf = row.id === currentUserId;

  return (
    <div className="grid gap-3 rounded-xl border border-line bg-white p-4 lg:grid-cols-[minmax(0,1fr)_auto_auto_auto] lg:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="truncate text-sm font-black text-ink">{row.email}</span>
          {!row.is_active && <Badge tone="critical">inactive</Badge>}
          {isSelf && <Badge tone="info">you</Badge>}
        </div>
        <p className="mt-1 text-xs text-muted">
          {row.display_name || "—"} · joined {formatWhen(row.created_at)}
        </p>
      </div>
      <select
        value={role}
        disabled={saving}
        onChange={(e) => setRole(e.target.value)}
        className="rounded-lg border border-line bg-white px-3 py-2 text-sm font-bold text-ink focus:outline-none focus:ring-1 focus:ring-brand"
      >
        {ROLES.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
      <label className="flex items-center gap-2 text-xs font-bold text-muted">
        <input
          type="checkbox"
          checked={active}
          disabled={saving || isSelf}
          onChange={(e) => setActive(e.target.checked)}
          className="h-4 w-4 rounded border-line"
        />
        Active
      </label>
      <Button
        variant="primary"
        size="sm"
        disabled={!dirty || saving}
        onClick={() => onSave(row.id, role, active)}
      >
        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
      </Button>
    </div>
  );
}

export function UsersPanel() {
  const whoami = useAuthWhoami();
  const isAdmin = useMemo(
    () =>
      Boolean(
        whoami.data?.role === "admin" ||
          whoami.data?.scopes.includes("auth_admin"),
      ),
    [whoami.data],
  );
  const users = useAuthUsers({ enabled: isAdmin });
  const updateUser = useUpdateAuthUserMutation();

  const save = async (userId: string, role: string, isActive: boolean) => {
    try {
      await updateUser.mutateAsync({
        userId,
        payload: { role, is_active: isActive },
      });
      notify.success("User updated");
    } catch (err) {
      notify.error(String((err as Error).message));
    }
  };

  if (whoami.isPending) return null;

  if (!isAdmin) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-brand" />
            Users & roles
          </CardTitle>
          <CardDescription>
            Assign TrustOps roles within your tenant — separate from IdP groups
            unless role sync is enabled server-side.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="rounded-lg border border-line bg-slate-50 p-4 text-sm text-muted">
            Only workspace admins can change user roles. Your current role is{" "}
            <span className="font-black text-ink">{whoami.data?.role}</span>.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserCog className="h-5 w-5 text-brand" />
          Users & roles
        </CardTitle>
        <CardDescription>
          Make Alice admin, demote contributors, or deactivate accounts. Last
          active admin cannot be demoted or deactivated.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <QueryState queries={[users]} label="users">
          {(users.data ?? []).map((row) => (
            <UserRow
              key={row.id}
              row={row}
              currentUserId={whoami.data?.user_id}
              saving={updateUser.isPending}
              onSave={save}
            />
          ))}
        </QueryState>
        <p className="text-xs leading-5 text-muted">
          IdP group → role mapping uses{" "}
          <code className="text-ink">TRUSTOPS_OIDC_ROLE_MAP</code> on SSO login
          when sync is enabled. Manual changes here override until the next IdP
          sync if configured.
        </p>
      </CardContent>
    </Card>
  );
}
