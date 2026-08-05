import type { SxProps, Theme } from "@mui/material/styles";

/** Subtle lift/highlight applied to calendar event chips on hover. */
export const calendarEventHoverSx: SxProps<Theme> = {
  transition: (theme) =>
    theme.transitions.create(["transform", "box-shadow", "filter"], {
      duration: theme.transitions.duration.shortest,
    }),
  "&:hover": {
    transform: "translateY(-1px)",
    filter: "brightness(1.08)",
    boxShadow: 1,
  },
};

/** Background tint applied to a calendar month-view day cell on hover. */
export const calendarDayHoverSx: SxProps<Theme> = {
  transition: (theme) =>
    theme.transitions.create("background-color", {
      duration: theme.transitions.duration.shortest,
    }),
  "&:hover": {
    bgcolor: "action.hover",
  },
};

/** Hover treatment for the day-number badge inside a calendar month-view cell. */
export const calendarDayNumberSx: SxProps<Theme> = {
  transition: (theme) =>
    theme.transitions.create(["background-color", "color"], {
      duration: theme.transitions.duration.shortest,
    }),
};
