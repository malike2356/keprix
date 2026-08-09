import { useStore } from '@nanostores/react'
import type { ReactNode } from 'react'
import { useState } from 'react'

import { ErrorBoundary } from '@/components/error-boundary'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Loader } from '@/components/ui/loader'
import { useI18n } from '@/i18n'
import { selectDesktopPaths } from '@/lib/desktop-fs'
import {
  createDesktopVaultFolder,
  createDesktopVaultNote,
  readDesktopVaultContent,
  trashDesktopVaultItem,
  type DesktopVaultItem
} from '@/lib/desktop-vault-api'
import { normalizeOrLocalPreviewTarget } from '@/lib/local-preview'
import { cn } from '@/lib/utils'
import { $panesFlipped } from '@/store/layout'
import { notifyError } from '@/store/notifications'
import { setCurrentSessionPreviewTarget } from '@/store/preview'
import { $currentCwd } from '@/store/session'

import { SidebarPanelLabel } from '../shell/sidebar-label'

import { RemoteFolderPicker } from './files/remote-picker'
import { ProjectTree } from './files/tree'
import { useDocumentVaultTree } from './files/use-document-vault-tree'
import { useProjectTree } from './files/use-project-tree'

type SidebarMode = 'host' | 'vault'

interface RightSidebarPaneProps {
  onActivateFile: (path: string) => void
  onActivateFolder: (path: string) => void
  onChangeCwd: (path: string) => Promise<void> | void
}

export function RightSidebarPane({ onActivateFile, onActivateFolder, onChangeCwd }: RightSidebarPaneProps) {
  const { t } = useI18n()
  const r = t.rightSidebar
  const panesFlipped = useStore($panesFlipped)
  const currentCwd = useStore($currentCwd).trim()
  const hasCwd = currentCwd.length > 0
  const [mode, setMode] = useState<SidebarMode>('vault')
  const [vaultPreview, setVaultPreview] = useState<{ name: string; content: string } | null>(null)

  const {
    collapseAll,
    collapseNonce,
    data,
    effectiveCwd,
    loadChildren,
    openState,
    refreshRoot,
    rootError,
    rootLoading,
    setNodeOpen
  } = useProjectTree(currentCwd)

  const vault = useDocumentVaultTree()

  const cwdName = hasCwd
    ? (effectiveCwd
        .split(/[\\/]+/)
        .filter(Boolean)
        .pop() ?? effectiveCwd)
    : r.noFolderSelected

  const canCollapse = Object.values(openState).some(Boolean)

  const chooseFolder = async () => {
    const selected = await selectDesktopPaths({
      defaultPath: hasCwd ? effectiveCwd : undefined,
      directories: true,
      multiple: false,
      title: r.changeCwdTitle
    })

    if (selected?.[0]) {
      await onChangeCwd(selected[0])
    }
  }

  const previewFile = async (path: string) => {
    try {
      const preview = await normalizeOrLocalPreviewTarget(path, effectiveCwd || undefined)

      if (!preview) {
        throw new Error(r.couldNotPreview(path))
      }

      setCurrentSessionPreviewTarget(preview, 'file-browser', path)
    } catch (error) {
      notifyError(error, r.previewUnavailable)
    }
  }

  const openVaultItem = async (item: DesktopVaultItem) => {
    if (item.kind === 'folder') {
      vault.openFolder(item)
      setVaultPreview(null)
      return
    }
    try {
      const payload = await readDesktopVaultContent(item.id)
      setVaultPreview({ name: item.name, content: payload.content || '' })
    } catch (error) {
      notifyError(error, r.previewUnavailable)
    }
  }

  return (
    <aside
      aria-label={r.aria}
      className={cn(
        'before:pointer-events-none relative flex h-full w-full min-w-0 flex-col overflow-hidden border-(--ui-stroke-secondary) bg-(--ui-sidebar-surface-background) pt-(--titlebar-height) text-(--ui-text-tertiary)',
        panesFlipped
          ? 'border-r shadow-[inset_-0.0625rem_0_0_color-mix(in_srgb,white_18%,transparent)]'
          : 'border-l shadow-[inset_0.0625rem_0_0_color-mix(in_srgb,white_18%,transparent)]'
      )}
    >
      <div className="flex gap-1 border-b border-(--ui-stroke-secondary) px-2 py-1.5" role="tablist" aria-label={r.panelsAria}>
        <Button
          aria-selected={mode === 'vault'}
          className={cn('flex-1 text-xs', mode === 'vault' && 'bg-sidebar-accent')}
          onClick={() => setMode('vault')}
          role="tab"
          size="sm"
          type="button"
          variant="ghost"
        >
          Document Vault
        </Button>
        <Button
          aria-selected={mode === 'host'}
          className={cn('flex-1 text-xs', mode === 'host' && 'bg-sidebar-accent')}
          onClick={() => setMode('host')}
          role="tab"
          size="sm"
          type="button"
          variant="ghost"
        >
          {r.files}
        </Button>
      </div>

      {mode === 'host' ? (
        <>
          <RemoteFolderPicker />
          <FilesystemTab
            canCollapse={canCollapse}
            collapseNonce={collapseNonce}
            cwd={effectiveCwd}
            cwdName={cwdName}
            data={data}
            error={rootError}
            hasCwd={hasCwd}
            loading={rootLoading}
            onActivateFile={onActivateFile}
            onActivateFolder={onActivateFolder}
            onChangeFolder={chooseFolder}
            onCollapseAll={collapseAll}
            onLoadChildren={loadChildren}
            onNodeOpenChange={setNodeOpen}
            onPreviewFile={previewFile}
            onRefresh={() => void refreshRoot()}
            openState={openState}
          />
        </>
      ) : (
        <DocumentVaultTab
          crumbs={vault.crumbs}
          error={vault.error}
          items={vault.items}
          loading={vault.loading}
          onCreateFolder={async () => {
            try {
              await createDesktopVaultFolder('New folder', vault.parentId)
              await vault.refresh()
            } catch (error) {
              notifyError(error, 'Could not create folder')
            }
          }}
          onCreateNote={async () => {
            try {
              await createDesktopVaultNote('Untitled', vault.parentId)
              await vault.refresh()
            } catch (error) {
              notifyError(error, 'Could not create note')
            }
          }}
          onGoCrumb={vault.goCrumb}
          onOpen={item => void openVaultItem(item)}
          onRefresh={() => void vault.refresh()}
          onTrash={async item => {
            try {
              await trashDesktopVaultItem(item.id)
              if (vaultPreview?.name === item.name) setVaultPreview(null)
              await vault.refresh()
            } catch (error) {
              notifyError(error, 'Could not trash item')
            }
          }}
          preview={vaultPreview}
        />
      )}
    </aside>
  )
}


const HEADER_ACTION_CLASS =
  'text-sidebar-foreground/70 hover:bg-sidebar-accent! hover:text-sidebar-accent-foreground! focus-visible:ring-sidebar-ring'

const HEADER_ACTION_LABEL_REVEAL = `${HEADER_ACTION_CLASS} pointer-events-none opacity-0 transition-opacity focus-visible:pointer-events-auto focus-visible:opacity-100 group-focus-within/project-header:pointer-events-auto group-focus-within/project-header:opacity-100 group-hover/project-header:pointer-events-auto group-hover/project-header:opacity-100`

interface DocumentVaultTabProps {
  crumbs: Array<{ id: string | null; name: string }>
  error: string | null
  items: DesktopVaultItem[]
  loading: boolean
  onCreateFolder: () => Promise<void>
  onCreateNote: () => Promise<void>
  onGoCrumb: (index: number) => void
  onOpen: (item: DesktopVaultItem) => void
  onRefresh: () => void
  onTrash: (item: DesktopVaultItem) => Promise<void>
  preview: { name: string; content: string } | null
}

function DocumentVaultTab({
  crumbs,
  error,
  items,
  loading,
  onCreateFolder,
  onCreateNote,
  onGoCrumb,
  onOpen,
  onRefresh,
  onTrash,
  preview
}: DocumentVaultTabProps) {
  const { t } = useI18n()
  const r = t.rightSidebar

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <RightSidebarSectionHeader>
        <SidebarPanelLabel>Document Vault</SidebarPanelLabel>
        <Button aria-label={r.refreshTree} className={HEADER_ACTION_CLASS} onClick={onRefresh} size="icon-xs" variant="ghost">
          <Codicon name="refresh" size="0.8125rem" spinning={loading} />
        </Button>
        <Button aria-label="New folder" className={HEADER_ACTION_CLASS} onClick={() => void onCreateFolder()} size="icon-xs" variant="ghost">
          <Codicon name="new-folder" size="0.8125rem" />
        </Button>
        <Button aria-label="New note" className={HEADER_ACTION_CLASS} onClick={() => void onCreateNote()} size="icon-xs" variant="ghost">
          <Codicon name="new-file" size="0.8125rem" />
        </Button>
      </RightSidebarSectionHeader>

      <div className="flex flex-wrap gap-1 px-2 pb-1 text-[0.6875rem] text-(--ui-text-tertiary)">
        {crumbs.map((crumb, index) => (
          <button
            className="hover:text-(--ui-text-secondary)"
            key={`${crumb.id}-${index}`}
            onClick={() => onGoCrumb(index)}
            type="button"
          >
            {crumb.name}
            {index < crumbs.length - 1 ? ' /' : ''}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-1 pb-2">
        {loading ? (
          <div className="flex items-center gap-2 px-2 py-3 text-xs">
            <Loader className="size-4" type="spiral-search" />
            Loading Document Vault
          </div>
        ) : error ? (
          <div className="px-2 py-3 text-xs text-destructive">{error}</div>
        ) : items.length === 0 ? (
          <div className="px-2 py-3 text-xs">Vault is empty. Create a folder or note.</div>
        ) : (
          <ul className="space-y-0.5">
            {items.map(item => (
              <li key={item.id}>
                <div className="flex w-full items-center gap-1 rounded px-2 py-1 text-xs hover:bg-(--ui-row-hover-background)">
                  <button className="flex min-w-0 flex-1 items-center gap-1 text-left" onClick={() => onOpen(item)} type="button">
                    <Codicon name={item.kind === 'folder' ? 'folder' : 'file'} size="0.75rem" />
                    <span className="min-w-0 flex-1 truncate">{item.name}</span>
                  </button>
                  <button
                    aria-label={`Trash ${item.name}`}
                    className="opacity-60 hover:opacity-100"
                    onClick={() => void onTrash(item)}
                    type="button"
                  >
                    <Codicon name="trash" size="0.75rem" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
        {preview ? (
          <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded border border-(--ui-stroke-secondary) p-2 text-[0.65rem]">
            <div className="mb-1 font-semibold">{preview.name}</div>
            {preview.content.slice(0, 4000)}
          </pre>
        ) : null}
      </div>
      <p className="border-t border-(--ui-stroke-secondary) px-2 py-1 text-[0.625rem] text-(--ui-text-tertiary)">
        Tenant vault only. Host project tree is under File system.
      </p>
    </div>
  )
}

interface FilesystemTabProps extends FileTreeBodyProps {
  canCollapse: boolean
  cwdName: string
  hasCwd: boolean
  onChangeFolder: () => Promise<void> | void
  onCollapseAll: () => void
  onRefresh: () => void
}

function FilesystemTab({
  canCollapse,
  collapseNonce,
  cwd,
  cwdName,
  data,
  error,
  hasCwd,
  loading,
  onActivateFile,
  onActivateFolder,
  onChangeFolder,
  onCollapseAll,
  onLoadChildren,
  onNodeOpenChange,
  onPreviewFile,
  onRefresh,
  openState
}: FilesystemTabProps) {
  const { t } = useI18n()
  const r = t.rightSidebar

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <RightSidebarSectionHeader>
        <div className="flex min-w-0 flex-1">
          <button
            className="flex w-full min-w-0 items-center rounded-md text-left hover:text-(--ui-text-secondary)"
            onClick={() => void onChangeFolder()}
            type="button"
          >
            <SidebarPanelLabel>{cwdName}</SidebarPanelLabel>
          </button>
        </div>
        <Button
          aria-label={r.refreshTree}
          className={HEADER_ACTION_LABEL_REVEAL}
          disabled={!hasCwd || loading}
          onClick={onRefresh}
          size="icon-xs"
          variant="ghost"
        >
          <Codicon name="refresh" size="0.8125rem" spinning={loading} />
        </Button>
        <Button
          aria-label={r.openFolder}
          className={HEADER_ACTION_CLASS}
          onClick={() => void onChangeFolder()}
          size="icon-xs"
          variant="ghost"
        >
          <Codicon name="folder-opened" size="0.8125rem" />
        </Button>
        <Button
          aria-label={r.collapseAll}
          className={cn(HEADER_ACTION_CLASS, !canCollapse && 'pointer-events-none opacity-0')}
          disabled={!hasCwd || !canCollapse}
          onClick={onCollapseAll}
          size="icon-xs"
          variant="ghost"
        >
          <Codicon name="collapse-all" size="0.8125rem" />
        </Button>
      </RightSidebarSectionHeader>
      <FileTreeBody
        collapseNonce={collapseNonce}
        cwd={cwd}
        data={data}
        error={error}
        loading={loading}
        onActivateFile={onActivateFile}
        onActivateFolder={onActivateFolder}
        onLoadChildren={onLoadChildren}
        onNodeOpenChange={onNodeOpenChange}
        onPreviewFile={onPreviewFile}
        onRetry={onRefresh}
        openState={openState}
      />
    </div>
  )
}

export function RightSidebarSectionHeader({ children }: { children: ReactNode }) {
  return <div className="group/project-header flex h-7 shrink-0 items-center px-2.5">{children}</div>
}

interface FileTreeBodyProps {
  collapseNonce: number
  cwd: string
  data: ReturnType<typeof useProjectTree>['data']
  error: string | null
  loading: boolean
  onActivateFile: (path: string) => void
  onActivateFolder: (path: string) => void
  onLoadChildren: (id: string) => void | Promise<void>
  onNodeOpenChange: (id: string, open: boolean) => void
  onPreviewFile?: (path: string) => void
  /** Force-reload the root. The hook also auto-retries while errored, so this
   *  is the impatient-user path. */
  onRetry?: () => void
  openState: ReturnType<typeof useProjectTree>['openState']
}

function FileTreeBody({
  collapseNonce,
  cwd,
  data,
  error,
  loading,
  onActivateFile,
  onActivateFolder,
  onLoadChildren,
  onNodeOpenChange,
  onPreviewFile,
  onRetry,
  openState
}: FileTreeBodyProps) {
  const { t } = useI18n()
  const r = t.rightSidebar

  if (!cwd) {
    return <EmptyState body={r.noProjectBody} title={r.noProjectTitle} />
  }

  if (error) {
    return (
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-2 px-4 text-center">
        <EmptyState body={r.unreadableBody(error)} title={r.unreadableTitle} />
        {onRetry && (
          <button
            className="text-[0.68rem] font-medium text-muted-foreground transition hover:text-foreground"
            onClick={onRetry}
            type="button"
          >
            {r.tryAgain}
          </button>
        )}
      </div>
    )
  }

  if (loading && data.length === 0) {
    return <FileTreeLoadingState />
  }

  if (data.length === 0) {
    return <EmptyState body={r.emptyBody} title={r.emptyTitle} />
  }

  return (
    <ErrorBoundary
      fallback={({ reset }) => (
        <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-2 px-4 text-center">
          <EmptyState body={r.treeErrorBody} title={r.treeErrorTitle} />
          <button
            className="text-[0.68rem] font-medium text-muted-foreground transition hover:text-foreground"
            onClick={reset}
            type="button"
          >
            {r.tryAgain}
          </button>
        </div>
      )}
      key={cwd}
      label="file-tree"
    >
      <ProjectTree
        collapseNonce={collapseNonce}
        cwd={cwd}
        data={data}
        onActivateFile={onActivateFile}
        onActivateFolder={onActivateFolder}
        onLoadChildren={onLoadChildren}
        onNodeOpenChange={onNodeOpenChange}
        onPreviewFile={onPreviewFile}
        openState={openState}
      />
    </ErrorBoundary>
  )
}

function FileTreeLoadingState() {
  const { t } = useI18n()

  return (
    <div aria-label={t.rightSidebar.loadingTree} className="grid min-h-0 flex-1 place-items-center px-3" role="status">
      <Loader
        aria-hidden="true"
        className="size-8 text-(--ui-text-tertiary)"
        pathSteps={180}
        role="presentation"
        strokeScale={0.68}
        type="spiral-search"
      />
    </div>
  )
}

function EmptyState({ body, title }: { body: string; title: string }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-1 px-4 text-center">
      <div className="text-[0.7rem] font-semibold uppercase tracking-[0.07em] text-muted-foreground/75">{title}</div>
      <div className="text-[0.68rem] leading-relaxed text-muted-foreground/65">{body}</div>
    </div>
  )
}
