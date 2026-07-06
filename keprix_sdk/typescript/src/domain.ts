export interface Field {
  name: string;
  type?: string;
  required?: boolean;
  default?: unknown;
  entity?: string;
  values?: string[];
}

export interface Operation {
  name: string;
  confirmation_required?: boolean;
}

export interface Entity {
  name: string;
  fields?: Field[];
  operations?: Operation[];
}

export interface Domain {
  name: string;
  entities?: Entity[];
}
