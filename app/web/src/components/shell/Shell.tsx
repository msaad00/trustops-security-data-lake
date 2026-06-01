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

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const normalizedPathname = pathname.replace(/\/$/, "");
  const isLoginRoute =
    normalizedPathname === "/login" || normalizedPathname.endsWith("/login");
  const qc = useQueryClient();
  const [toast, setToast] = useState<string | null>(null);
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const flash = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 4200);
  }, []);

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

  if (isLoginRoute) {
    return <div className="min-h-screen bg-panel">{children}</div>;
  }

  return (
    <div className="grid min-h-screen grid-rows-[78px_auto_auto_1fr] bg-rail">
      <TopBar
        onRefresh={onRefresh}
        onSnapshot={onSnapshot}
        onOpenPalette={() => setPaletteOpen(true)}
      />
      <AuditorBanner />
      <div className="grid grid-cols-[auto_minmax(0,1fr)]">
        <Sidebar />
        <div className="grid grid-rows-[auto_1fr] overflow-hidden">
          <Breadcrumbs />
          <main className="overflow-auto bg-panel">
            <ApiHealthBanner />
            {children}
          </main>
        </div>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
      <SnapshotModal
        open={snapshotOpen}
        onClose={() => setSnapshotOpen(false)}
        onToast={flash}
      />
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            className="fixed bottom-6 left-1/2 z-[60] max-w-[520px] -translate-x-1/2 rounded-lg bg-[#111827] px-3.5 py-3 text-sm text-white shadow-hero"
          >
            {toast}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
