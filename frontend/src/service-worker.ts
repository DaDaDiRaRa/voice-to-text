/**
 * Service Worker — Vite PWA injectManifest 전략.
 *
 * 기능:
 * 1. 정적 자산 precache (Workbox inject)
 * 2. API 요청 NetworkFirst 전략
 * 3. Background Sync — 오프라인 녹음 자동 업로드
 */

/// <reference lib="WebWorker" />
/// <reference types="vite/client" />

import { cleanupOutdatedCaches, precacheAndRoute } from "workbox-precaching";
import { registerRoute } from "workbox-routing";
import { NetworkFirst, NetworkOnly } from "workbox-strategies";

declare const self: ServiceWorkerGlobalScope;

// Vite PWA가 빌드 시 주입하는 precache manifest
precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

// ── API 라우트: NetworkFirst (오프라인 시 캐시 fallback) ──────────────────────
registerRoute(
  ({ url }) => url.pathname.startsWith("/api/structure") || url.pathname.startsWith("/api/transcribe"),
  new NetworkFirst({ cacheName: "api-cache", networkTimeoutSeconds: 30 })
);

// ── export는 항상 네트워크 필요 ───────────────────────────────────────────────
registerRoute(
  ({ url }) => url.pathname.startsWith("/api/export"),
  new NetworkOnly()
);

// ── Background Sync — 오프라인 녹음 업로드 ───────────────────────────────────
const SYNC_TAG = "sync-recordings";

self.addEventListener("sync", (event) => {
  if (event.tag === SYNC_TAG) {
    event.waitUntil(flushPendingRecordings());
  }
});

async function flushPendingRecordings(): Promise<void> {
  // IndexedDB에서 pending 목록 읽기 (idb를 SW 내부에서 직접 사용)
  const db = await openPendingDB();
  const all = await getAllFromStore(db);

  for (const record of all) {
    try {
      const form = new FormData();
      form.append("file", record.blob, record.filename);

      const transcribeRes = await fetch("/api/transcribe", { method: "POST", body: form });
      if (!transcribeRes.ok) continue;

      const { transcript } = await transcribeRes.json() as { transcript: string };

      const structureRes = await fetch("/api/structure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript, mode: record.mode, metadata: record.metadata }),
      });
      if (!structureRes.ok) continue;

      const structured = await structureRes.json();

      // 처리 결과를 클라이언트에 전달
      const clients = await self.clients.matchAll({ type: "window" });
      for (const client of clients) {
        client.postMessage({ type: "SYNC_RESULT", payload: { ...structured, id: record.id } });
      }

      await deleteFromStore(db, record.id);
    } catch {
      // 다음 sync 시도 때 재처리
    }
  }
}

// ── 경량 IndexedDB 헬퍼 (idb 미사용 — SW 내 번들 최소화) ────────────────────
interface PendingRecord {
  id: number;
  blob: Blob;
  filename: string;
  mode: string;
  metadata?: object;
}

function openPendingDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("voice-to-text", 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("pending-recordings")) {
        db.createObjectStore("pending-recordings", { keyPath: "id", autoIncrement: true });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function getAllFromStore(db: IDBDatabase): Promise<PendingRecord[]> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("pending-recordings", "readonly");
    const req = tx.objectStore("pending-recordings").getAll();
    req.onsuccess = () => resolve(req.result as PendingRecord[]);
    req.onerror = () => reject(req.error);
  });
}

function deleteFromStore(db: IDBDatabase, id: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("pending-recordings", "readwrite");
    const req = tx.objectStore("pending-recordings").delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// ── SW 설치·활성화 ────────────────────────────────────────────────────────────
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
