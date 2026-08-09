/** Desktop Document Vault API (tenant vault; never host /api/fs). */

export type DesktopVaultItem = {
  id: string
  kind: string
  name: string
  parent_id?: string | null
  trashed?: boolean
  trashed_at?: string | null
  byte_size?: number
}

function bridge() {
  const desktop = window.hermesDesktop
  if (!desktop) {
    throw new Error('Hermes Desktop bridge is unavailable')
  }
  return desktop
}

export async function listDesktopVaultItems(opts?: {
  parentId?: string | null
  includeTrashed?: boolean
}): Promise<{ items: DesktopVaultItem[] }> {
  const params = new URLSearchParams()
  if (opts?.parentId) params.set('parent_id', opts.parentId)
  if (opts?.includeTrashed) params.set('include_trashed', 'true')
  const qs = params.toString()
  const path = `/api/document-vault/items${qs ? `?${qs}` : ''}`
  return bridge().api<{ items: DesktopVaultItem[] }>({ path })
}

export async function createDesktopVaultFolder(name: string, parentId?: string | null) {
  return bridge().api<DesktopVaultItem>({
    path: '/api/document-vault/items',
    method: 'POST',
    body: { kind: 'folder', name, parent_id: parentId ?? null }
  })
}

export async function createDesktopVaultNote(name: string, parentId?: string | null) {
  return bridge().api<DesktopVaultItem>({
    path: '/api/document-vault/items',
    method: 'POST',
    body: {
      kind: 'markdown',
      name,
      content: `# ${name}\n\n`,
      parent_id: parentId ?? null
    }
  })
}

export async function moveDesktopVaultItem(itemId: string, parentId: string | null) {
  return bridge().api<DesktopVaultItem>({
    path: `/api/document-vault/items/${encodeURIComponent(itemId)}/move`,
    method: 'POST',
    body: { parent_id: parentId }
  })
}

export async function trashDesktopVaultItem(itemId: string) {
  return bridge().api<DesktopVaultItem>({
    path: `/api/document-vault/items/${encodeURIComponent(itemId)}/trash`,
    method: 'POST'
  })
}

export async function readDesktopVaultContent(itemId: string) {
  return bridge().api<{ item_id: string; content: string }>({
    path: `/api/document-vault/items/${encodeURIComponent(itemId)}/content`
  })
}
