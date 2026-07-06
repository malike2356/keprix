"use client";

import FormControl from "@mui/material/FormControl";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import WorkspacesOutlinedIcon from "@mui/icons-material/WorkspacesOutlined";
import * as React from "react";

type WorkspaceSwitcherProps = {
  workspaceId?: string;
  workspaceName?: string;
};

export default function WorkspaceSwitcher({
  workspaceId = "default",
  workspaceName = "Default workspace",
}: WorkspaceSwitcherProps) {
  const [value, setValue] = React.useState(workspaceId);

  return (
    <FormControl size="small" sx={{ minWidth: 180 }}>
      <Select
        value={value}
        onChange={(e) => setValue(e.target.value)}
        displayEmpty
        renderValue={() => (
          <Typography variant="body2" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <WorkspacesOutlinedIcon sx={{ fontSize: 18 }} />
            {workspaceName}
          </Typography>
        )}
      >
        <MenuItem value={workspaceId}>{workspaceName}</MenuItem>
      </Select>
    </FormControl>
  );
}
