export const draftStorageKey = "carbon-research-draft-v1";
export const starterSeenKey = "carbon-research-starter-seen-v1";

type StorageReader = Pick<Storage, "getItem">;

export function shouldLoadStarterExample(storage: StorageReader, browserMode: boolean, hasSavedProject: boolean): boolean {
  if (!browserMode || storage.getItem(starterSeenKey)) return false;
  if (hasSavedProject) return false;
  const saved = storage.getItem(draftStorageKey);
  if (!saved) return true;
  try {
    const draft = JSON.parse(saved) as {
      name?: string;
      rows?: Array<{ item_name?: string }>;
      tver?: unknown;
    };
    return !draft.name?.trim() && !draft.rows?.some((row) => row.item_name?.trim()) && !draft.tver;
  } catch {
    return true;
  }
}
