"use client";

import { useCallback, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { Breadcrumbs } from "./Breadcrumbs";
import { CommandPalette } from "./CommandPalette";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { ApiHealthBanner } from "@/components/ApiHealthBanner";
import { AuditorBanner } from "@/components/AuditorBanner";
import { SnapshotModal } from "@/components/modals/SnapshotModal";
import { api } from "@/lib/api/client";
import { notify } from "@/lib/toast";

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const normalizedPathname = pathname.replace(/\/$/, "");
  const isLoginRoute =
    normalizedPathname === "/login" || normalizedPathname.endsWith("/login");
  // The public trust center is rendered for unauthenticated external reviewers
  // holding a token; it must bypass the authed Shell (nav, auditor banner,
  // API-health probes) entirely, the same way /login does.
  const isPublicTrustRoute = /(^|\/)trust\/[^/]+$/.test(normalizedPathname);
  const qc = useQueryClient();
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const flash = useCallback((msg: string) => notify.success(msg), []);

  const onRefresh = useCallback(async () => {
    await qc.invalidateQueries();
    flash("Posture refreshed from assessment data");
  }, [qc, flash]);

  const onSnapshot = useCallback(async () => {
    setSnapshotOpen(true);
    // Pre-warm the snapshot list so the modal already has the latest record.
    try {
      await api.listSnapshots();
    } catch {
      /* non-blocking */
    }
  }, []);

  if (isLoginRoute || isPublicTrustRoute) {
    return <div className="min-h-screen bg-panel">{children}</div>;
  }

  return (
    <div className="flex h-dvh min-h-0 w-full min-w-0 max-w-none flex-col overflow-hidden bg-rail">
      <TopBar
        onRefresh={onRefresh}
        onSnapshot={onSnapshot}
        onOpenPalette={() => setPaletteOpen(true)}
      />
      <AuditorBanner />
      <div className="grid min-h-0 min-w-0 flex-1 grid-cols-[auto_minmax(0,1fr)] overflow-hidden">
        <Sidebar />
        <div className="grid min-h-0 min-w-0 grid-rows-[auto_minmax(0,1fr)] overflow-hidden">
          <Breadcrumbs />
          <main className="min-h-0 min-w-0 max-w-full overflow-auto bg-panel">
            <ApiHealthBanner />
            <AnimatePresence mode="wait">
              <motion.div
                key={normalizedPathname}
                className="min-w-0"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.16, ease: "easeOut" }}
              >
                {children}
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
      </div>
      <CommandPalette
        open={paletteOpen}
        onOpenChange={setPaletteOpen}
        onSnapshot={onSnapshot}
        onRefresh={onRefresh}
      />
      <SnapshotModal
        open={snapshotOpen}
        onClose={() => setSnapshotOpen(false)}
        onToast={flash}
      />
    </div>
  );
}
