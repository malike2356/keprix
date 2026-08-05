"use client";

import ExtensionIcon from "@mui/icons-material/Extension";
import Chip from "@mui/material/Chip";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import ListItemText from "@mui/material/ListItemText";
import * as React from "react";
import { useRouter } from "next/navigation";

export type SuggestedConnector = {
  id: string;
  label: string;
  reason?: string;
  category?: string;
};

type Props = {
  connectors: SuggestedConnector[];
};

export default function SuggestConnectorChip({ connectors }: Props) {
  const router = useRouter();
  const [anchorEl, setAnchorEl] = React.useState<HTMLElement | null>(null);

  if (connectors.length === 0) return null;

  const openMenu = (event: React.MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget);
  const closeMenu = () => setAnchorEl(null);

  const goToConnector = (id: string) => {
    closeMenu();
    router.push(`/integrations?id=${encodeURIComponent(id)}`);
  };

  const label =
    connectors.length === 1 ? `Try ${connectors[0].label}` : `${connectors.length} suggested connectors`;

  return (
    <>
      <Chip
        size="small"
        icon={<ExtensionIcon fontSize="small" />}
        label={label}
        variant="outlined"
        color="info"
        onClick={openMenu}
      />
      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={closeMenu}>
        {connectors.map((connector) => (
          <MenuItem key={connector.id} onClick={() => goToConnector(connector.id)}>
            <ListItemText primary={connector.label} secondary={connector.reason} />
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
