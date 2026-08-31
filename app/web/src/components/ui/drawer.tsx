"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface DrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  width?: "md" | "lg";
}

export function Drawer({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  width = "md",
}: DrawerProps) {
  const widthClass =
    width === "lg"
      ? "w-[min(560px,calc(100vw-16px))]"
      : "w-[min(460px,calc(100vw-16px))]";
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay forceMount asChild>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-sm"
              />
            </Dialog.Overlay>
            <Dialog.Content forceMount asChild>
              <motion.aside
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ type: "spring", stiffness: 320, damping: 32 }}
                className={cn(
                  "fixed bottom-0 right-0 top-0 z-50 flex max-w-full flex-col bg-white shadow-hero",
                  widthClass,
                )}
              >
                <header className="flex items-start justify-between gap-3 border-b border-line p-3 sm:p-4">
                  <div>
                    <Dialog.Title className="text-lg font-black text-ink">
                      {title}
                    </Dialog.Title>
                    {description && (
                      <Dialog.Description className="mt-1 text-sm text-muted">
                        {description}
                      </Dialog.Description>
                    )}
                  </div>
                  <Dialog.Close
                    aria-label="Close"
                    className="grid h-8 w-8 place-items-center rounded-md text-muted hover:bg-slate-100"
                  >
                    <X className="h-4 w-4" />
                  </Dialog.Close>
                </header>
                <div className="flex-1 overflow-auto p-3 sm:p-4">
                  {children}
                </div>
                {footer && (
                  <footer className="border-t border-line p-3 sm:p-4">
                    {footer}
                  </footer>
                )}
              </motion.aside>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
