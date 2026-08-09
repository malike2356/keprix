import { useCallback, useEffect, useState } from 'react'

import {
  listDesktopVaultItems,
  moveDesktopVaultItem,
  type DesktopVaultItem
} from '@/lib/desktop-vault-api'
import { notifyError } from '@/store/notifications'

export type VaultTreeNode = {
  id: string
  name: string
  kind: string
  children?: VaultTreeNode[] | null
}

export function useDocumentVaultTree() {
  const [parentId, setParentId] = useState<string | null>(null)
  const [crumbs, setCrumbs] = useState<Array<{ id: string | null; name: string }>>([
    { id: null, name: 'Document Vault' }
  ])
  const [items, setItems] = useState<DesktopVaultItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const payload = await listDesktopVaultItems({ parentId })
      setItems(payload.items || [])
    } catch (err) {
      setItems([])
      setError(err instanceof Error ? err.message : 'Failed to load Document Vault')
    } finally {
      setLoading(false)
    }
  }, [parentId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const openFolder = (item: DesktopVaultItem) => {
    if (item.kind !== 'folder') return
    setParentId(item.id)
    setCrumbs(prev => [...prev, { id: item.id, name: item.name }])
  }

  const goCrumb = (index: number) => {
    const target = crumbs[index]
    setCrumbs(crumbs.slice(0, index + 1))
    setParentId(target.id)
  }

  const moveWithRollback = async (itemId: string, folderId: string) => {
    const snapshot = items
    setItems(curr => curr.filter(row => row.id !== itemId))
    try {
      await moveDesktopVaultItem(itemId, folderId)
      await refresh()
    } catch (err) {
      setItems(snapshot)
      notifyError(err, 'Vault move failed; rolled back')
    }
  }

  return {
    crumbs,
    error,
    goCrumb,
    items,
    loading,
    moveWithRollback,
    openFolder,
    parentId,
    refresh,
    setParentId
  }
}
