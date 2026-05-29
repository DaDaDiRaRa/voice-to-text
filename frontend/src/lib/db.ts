/**
 * IndexedDB helper — 오프라인 녹음 임시 저장소.
 *
 * Store: "pending-recordings"
 * Key:   자동증가 id
 * Value: PendingRecording
 */

import { openDB, type IDBPDatabase } from "idb";
import type { Mode, FieldMetadata } from "./api";

export interface PendingRecording {
  id?: number;
  blob: Blob;
  filename: string;
  mode: Mode;
  metadata?: FieldMetadata;
  createdAt: number; // Date.now()
}

const DB_NAME = "voice-to-text";
const STORE = "pending-recordings";
const VERSION = 1;

let _db: IDBPDatabase | null = null;

async function db(): Promise<IDBPDatabase> {
  if (!_db) {
    _db = await openDB(DB_NAME, VERSION, {
      upgrade(database) {
        if (!database.objectStoreNames.contains(STORE)) {
          database.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
        }
      },
    });
  }
  return _db;
}

export async function savePending(recording: Omit<PendingRecording, "id">): Promise<number> {
  const d = await db();
  return (await d.add(STORE, recording)) as number;
}

export async function getAllPending(): Promise<PendingRecording[]> {
  const d = await db();
  return d.getAll(STORE);
}

export async function deletePending(id: number): Promise<void> {
  const d = await db();
  await d.delete(STORE, id);
}

export async function countPending(): Promise<number> {
  const d = await db();
  return d.count(STORE);
}
