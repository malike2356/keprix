export type BuiltAppNavItem = {
  id: string;
  label: string;
  href: string;
  icon?: string;
  badge?: number | string;
};

export type BuiltAppManifest = {
  id: string;
  label: string;
  description?: string;
  entry: string;
  icon?: string;
  version?: string;
  brand?: {
    primary_color?: string;
  };
  navigation?: {
    style?: "sections" | "sub_rail" | "tabs_only";
    items: BuiltAppNavItem[];
  };
};
