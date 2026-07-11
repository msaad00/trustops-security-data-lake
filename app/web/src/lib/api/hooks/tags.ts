"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import { LIVE, STALE, type Opts } from "./shared";
import type { EntityTag, SavedView, Tag } from "../types";

export function useTags(opts?: Opts<Tag[]>) {
  return useQuery({
    queryKey: ["tags"],
    queryFn: api.listTags,
    staleTime: STALE,
    refetchInterval: LIVE,
    ...opts,
  });
}

export function useCreateTagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; color?: string }) =>
      api.createTag(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tags"] }),
  });
}

export function useDeleteTagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tagId: string) => api.deleteTag(tagId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tags"] }),
  });
}

export function useAttachTagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      tag_id: string;
      entity_type: string;
      entity_id: string;
    }) => api.attachTag(payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["tags"] });
      qc.invalidateQueries({
        queryKey: ["tags-for", vars.entity_type, vars.entity_id],
      });
      qc.invalidateQueries({ queryKey: ["tag-entities"] });
    },
  });
}

export function useDetachTagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      tag_id: string;
      entity_type: string;
      entity_id: string;
    }) => api.detachTag(payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["tags"] });
      qc.invalidateQueries({
        queryKey: ["tags-for", vars.entity_type, vars.entity_id],
      });
      qc.invalidateQueries({ queryKey: ["tag-entities"] });
    },
  });
}

export function useTagEntityIds(
  tagId: string | null,
  entityType: string,
  opts?: Opts<string[]>,
) {
  return useQuery({
    queryKey: ["tag-entities", tagId, entityType],
    queryFn: async () => {
      if (!tagId) return [] as string[];
      return api.tagEntities(tagId, entityType);
    },
    enabled: Boolean(tagId),
    staleTime: STALE,
    ...opts,
  });
}

export function useTagsForEntity(
  entityType: string | null,
  entityId: string | null,
  opts?: Opts<Tag[]>,
) {
  return useQuery({
    queryKey: ["tags-for", entityType, entityId],
    queryFn: async () => {
      if (!entityType || !entityId) return [] as Tag[];
      return api.tagsForEntity(entityType, entityId);
    },
    enabled: Boolean(entityType && entityId),
    staleTime: STALE,
    ...opts,
  });
}

export function useSavedViews(surface?: string, opts?: Opts<SavedView[]>) {
  return useQuery({
    queryKey: ["saved-views", surface ?? null],
    queryFn: () => api.listSavedViews(surface),
    staleTime: STALE,
    refetchInterval: LIVE,
    ...opts,
  });
}

export function useCreateSavedViewMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      surface: string;
      name: string;
      filters: Record<string, unknown>;
    }) => api.createSavedView(payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["saved-views", vars.surface] });
      qc.invalidateQueries({ queryKey: ["saved-views", null] });
    },
  });
}

export function useDeleteSavedViewMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ viewId, surface }: { viewId: string; surface: string }) =>
      api.deleteSavedView(viewId).then((r) => ({ ...r, surface })),
    onSuccess: (_data) => {
      qc.invalidateQueries({ queryKey: ["saved-views"] });
    },
  });
}

export type { Tag, EntityTag, SavedView };
