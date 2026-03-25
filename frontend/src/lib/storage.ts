const DB_NAME = "aviator-store";
const DB_VERSION = 1;
const STORE = "history";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "timestamp" });
      }
    };
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

export async function storePoints(points: Array<{ timestamp: number; value: number; confidence: number }>) {
  const db = await openDb();
  const tx = db.transaction(STORE, "readwrite");
  const store = tx.objectStore(STORE);
  points.forEach((point) => store.put(point));
  await new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

export async function loadRecentPoints(limit = 300) {
  const db = await openDb();
  const tx = db.transaction(STORE, "readonly");
  const store = tx.objectStore(STORE);
  const request = store.getAll();
  const items: Array<{ timestamp: number; value: number; confidence: number }> = await new Promise(
    (resolve, reject) => {
      request.onsuccess = () => resolve(request.result ?? []);
      request.onerror = () => reject(request.error);
    }
  );
  db.close();
  return items
    .sort((a, b) => a.timestamp - b.timestamp)
    .slice(-limit);
}

export function getSetting(key: string, fallback = "") {
  return localStorage.getItem(key) ?? fallback;
}

export function setSetting(key: string, value: string) {
  localStorage.setItem(key, value);
}
