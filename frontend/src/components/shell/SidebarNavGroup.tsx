"use client";

import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { IconChevronRight, IconChevronDown } from "@tabler/icons-react";
import * as React from "react";

type SidebarNavGroupProps = {
  groupId: string;
  label: string;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
};

function scrollGroupIntoView(node: HTMLElement | null) {
  if (!node) return;
  node.scrollIntoView({
    block: "start",
    inline: "nearest",
    behavior: "smooth",
  });
}

export default function SidebarNavGroup({
  groupId,
  label,
  expanded,
  onToggle,
  children,
}: SidebarNavGroupProps) {
  const contentId = `sidebar-group-${groupId}`;
  const rootRef = React.useRef<HTMLDivElement>(null);
  const wasExpandedRef = React.useRef(expanded);

  React.useEffect(() => {
    const justOpened = expanded && !wasExpandedRef.current;
    wasExpandedRef.current = expanded;
    if (!justOpened) return;

    // Bring the header to the top of the scrollport before height settles.
    const frame = window.requestAnimationFrame(() => {
      scrollGroupIntoView(rootRef.current);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [expanded]);

  const handleEntered = React.useCallback(() => {
    // After collapse finishes, ensure the full open group stays on screen.
    scrollGroupIntoView(rootRef.current);
  }, []);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onToggle();
    }
  };

  return (
    <Box
      ref={rootRef}
      sx={{ mb: 1, scrollMarginTop: 1 }}
      data-sidebar-group={groupId}
      data-expanded={expanded ? "1" : "0"}
    >
      <Box
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        aria-controls={contentId}
        aria-label={`${label} navigation group`}
        onClick={onToggle}
        onKeyDown={handleKeyDown}
        sx={{
          mx: 1,
          px: 1.5,
          py: 1,
          borderRadius: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          color: "text.secondary",
          cursor: "pointer",
          "&:focus-visible": {
            outline: 2,
            outlineColor: "primary.main",
            outlineOffset: 2,
          },
          "&:hover": {
            bgcolor: "action.hover",
          },
        }}
      >
        <Typography variant="overline" sx={{ lineHeight: 1.4 }}>
          {label}
        </Typography>
        {expanded ? <IconChevronDown size={16} stroke={1.75} /> : <IconChevronRight size={16} stroke={1.75} />}
      </Box>
      <Collapse id={contentId} in={expanded} timeout="auto" onEntered={handleEntered}>
        {children}
      </Collapse>
    </Box>
  );
}
