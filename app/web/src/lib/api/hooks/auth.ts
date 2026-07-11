"use client";

import { useEffect, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { api, bootstrapAssessment } from "../client";
import { LIVE, STALE, type Opts } from "./shared";
import type {
  AuthApiKey,
  AuthMethods,
  AuthUser,
  AuthWhoami,
  CreateAuthKeyPayload,
  CreateInvitePayload,
  TenantInvite,
  UpdateAuthUserPayload,
} from "../types";

export function useAuthMethods(opts?: Opts<AuthMethods>) {
  return useQuery({
    queryKey: ["auth", "methods"],
    queryFn: api.authMethods,
    staleTime: STALE,
    retry: false,
    ...opts,
  });
}

export function useAuthWhoami(opts?: Opts<AuthWhoami>) {
  return useQuery({
    queryKey: ["auth", "whoami"],
    queryFn: api.authWhoami,
    staleTime: STALE,
    retry: false,
    ...opts,
  });
}

export function useAuthKeys(opts?: Opts<AuthApiKey[]>) {
  return useQuery({
    queryKey: ["auth", "keys"],
    queryFn: api.authKeys,
    staleTime: STALE,
    retry: false,
    ...opts,
  });
}

export function useCreateAuthKeyMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateAuthKeyPayload) => api.createAuthKey(payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["auth", "keys"] });
    },
  });
}

export function useRevokeAuthKeyMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => api.revokeAuthKey(keyId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["auth", "keys"] });
    },
  });
}

export function useAuthUsers(opts?: Opts<AuthUser[]>) {
  return useQuery({
    queryKey: ["auth", "users"],
    queryFn: api.authUsers,
    staleTime: STALE,
    retry: false,
    ...opts,
  });
}

export function useUpdateAuthUserMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      userId,
      payload,
    }: {
      userId: string;
      payload: UpdateAuthUserPayload;
    }) => api.updateAuthUser(userId, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["auth", "users"] });
      void qc.invalidateQueries({ queryKey: ["auth", "whoami"] });
    },
  });
}

export function useSessionFromKeyMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (apiKey: string) => api.sessionFromKey(apiKey),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["auth", "whoami"] });
    },
  });
}

export function useInvites(opts?: Opts<TenantInvite[]>) {
  return useQuery({
    queryKey: ["invites"],
    queryFn: api.invites,
    staleTime: STALE,
    retry: false,
    ...opts,
  });
}

export function useCreateInviteMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateInvitePayload) => api.createInvite(payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["invites"] });
    },
  });
}
