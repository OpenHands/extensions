const STORE_NAME = "database-snapshots";
const DATABASE_KEY = "sqlite";

export const APP_NAMESPACE = "browser-sql-lab";

export function makeDatabaseNamespace(backendId: string | null | undefined): string {
  const scopedBackend = backendId?.trim() || "unavailable-backend";
  return `${APP_NAMESPACE}::${encodeURIComponent(scopedBackend)}`;
}

export interface DatabaseStorage {
  load: () => Promise<Uint8Array | null>;
  save: (bytes: Uint8Array) => Promise<void>;
  clear: () => Promise<void>;
  close: () => void;
}

function actionableStorageError(message: string): Error {
  return new Error(
    `${message} Browser SQL Lab needs IndexedDB for browser-local persistence. ` +
      "Allow site storage for Canvas, then reload the App.",
  );
}

export async function openDatabaseStorage(namespace: string): Promise<DatabaseStorage> {
  if (typeof indexedDB === "undefined") {
    throw actionableStorageError("IndexedDB is unavailable.");
  }

  const database = await new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(namespace, 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE_NAME)) {
        request.result.createObjectStore(STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(actionableStorageError(request.error?.message ?? "IndexedDB could not be opened."));
    request.onblocked = () => reject(actionableStorageError("IndexedDB upgrade was blocked by another Canvas tab."));
  });

  const useStore = <T>(mode: IDBTransactionMode, operation: (store: IDBObjectStore) => IDBRequest<T>) =>
    new Promise<T>((resolve, reject) => {
      const transaction = database.transaction(STORE_NAME, mode);
      const request = operation(transaction.objectStore(STORE_NAME));
      let result: T;
      request.onsuccess = () => { result = request.result; };
      request.onerror = () => reject(actionableStorageError(request.error?.message ?? "IndexedDB request failed."));
      transaction.oncomplete = () => resolve(result);
      transaction.onerror = () => reject(actionableStorageError(transaction.error?.message ?? "IndexedDB transaction failed."));
      transaction.onabort = () => reject(actionableStorageError(transaction.error?.message ?? "IndexedDB transaction was aborted."));
    });

  return {
    async load() {
      const value = await useStore<ArrayBuffer | Uint8Array | undefined>("readonly", (store) => store.get(DATABASE_KEY));
      if (!value) return null;
      return value instanceof Uint8Array ? value : new Uint8Array(value);
    },
    async save(bytes) {
      const copy = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
      await useStore("readwrite", (store) => store.put(copy, DATABASE_KEY));
    },
    async clear() {
      await useStore("readwrite", (store) => store.delete(DATABASE_KEY));
    },
    close() {
      database.close();
    },
  };
}
