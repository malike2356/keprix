"use client";

import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import useMediaQuery from "@mui/material/useMediaQuery";
import * as React from "react";
import MobileActionSheet from "@/components/ui/MobileActionSheet";

export type ContextMenuItem = {
  id: string;
  label: string;
  destructive?: boolean;
  onClick: () => void | Promise<void>;
  dividerBefore?: boolean;
};

type ContextMenuProps = {
  open: boolean;
  position: { top: number; left: number } | null;
  items: ContextMenuItem[];
  title?: string;
  onClose: () => void;
};

export function ContextMenu({ open, position, items, title = "Actions", onClose }: ContextMenuProps) {
  const mobile = useMediaQuery("(max-width:699px)");
  const run = (item: ContextMenuItem) => {
    onClose();
    void item.onClick();
  };

  if (mobile) {
    return (
      <MobileActionSheet open={open} title={title} onClose={onClose}>
        {items.map((item) => (
          <React.Fragment key={item.id}>
            {item.dividerBefore ? <Divider /> : null}
            <Button
              fullWidth
              color={item.destructive ? "error" : "inherit"}
              sx={{ justifyContent: "flex-start" }}
              onClick={() => run(item)}
            >
              {item.label}
            </Button>
          </React.Fragment>
        ))}
      </MobileActionSheet>
    );
  }

  return (
    <Menu
      open={open}
      onClose={onClose}
      anchorReference="anchorPosition"
      anchorPosition={position || undefined}
    >
      {items.map((item) => [
        item.dividerBefore ? <Divider key={`${item.id}-divider`} /> : null,
        <MenuItem key={item.id} onClick={() => run(item)} sx={{ color: item.destructive ? "error.main" : undefined }}>
          {item.label}
        </MenuItem>,
      ])}
    </Menu>
  );
}

export function useContextMenu() {
  const [position, setPosition] = React.useState<{ top: number; left: number } | null>(null);
  const [items, setItems] = React.useState<ContextMenuItem[]>([]);
  const [title, setTitle] = React.useState("Actions");

  const openContextMenu = React.useCallback(
    (event: React.MouseEvent, nextItems: ContextMenuItem[], nextTitle = "Actions") => {
      event.preventDefault();
      event.stopPropagation();
      setPosition({ top: event.clientY, left: event.clientX });
      setItems(nextItems);
      setTitle(nextTitle);
    },
    [],
  );

  const closeContextMenu = React.useCallback(() => setPosition(null), []);

  return {
    openContextMenu,
    closeContextMenu,
    contextMenu: (
      <ContextMenu
        open={Boolean(position)}
        position={position}
        items={items}
        title={title}
        onClose={closeContextMenu}
      />
    ),
  };
}
