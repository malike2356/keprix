import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type CompaniesHouseStatus = {
  enabled: boolean;
  configured: boolean;
  api_key_set: boolean;
  api_base: string;
  docs: string;
};

export type CompanySearchHit = {
  company_number: string;
  title?: string | null;
  company_status?: string | null;
  company_type?: string | null;
  date_of_creation?: string | null;
  address_snippet?: string | null;
  description?: string | null;
  public_url?: string | null;
};

export type CompanySearchResult = {
  query: string;
  total_results?: number | null;
  items_per_page?: number;
  start_index?: number;
  items: CompanySearchHit[];
};

export type CompanyOfficer = {
  name?: string | null;
  officer_role?: string | null;
  appointed_on?: string | null;
  resigned_on?: string | null;
  nationality?: string | null;
  occupation?: string | null;
  country_of_residence?: string | null;
};

export type CompanyProfile = {
  company_number: string;
  company_name?: string | null;
  company_status?: string | null;
  company_status_detail?: string | null;
  type?: string | null;
  date_of_creation?: string | null;
  date_of_cessation?: string | null;
  jurisdiction?: string | null;
  sic_codes?: string[];
  has_been_liquidated?: boolean | null;
  has_insolvency_history?: boolean | null;
  has_charges?: boolean | null;
  registered_office_address?: {
    formatted?: string | null;
    address_line_1?: string | null;
    locality?: string | null;
    postal_code?: string | null;
    country?: string | null;
  } | null;
  officers?: CompanyOfficer[];
  public_url?: string | null;
};

async function parseJson<T>(res: Response, fallback: string): Promise<T> {
  const payload = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return payload as T;
}

export async function fetchCompaniesHouseStatus(): Promise<CompaniesHouseStatus> {
  return parseJson(await ceApi("/api/companies-house/status"), "Could not load Companies House status");
}

export async function saveCompaniesHouseSettings(body: {
  api_key?: string;
  enabled?: boolean;
}): Promise<CompaniesHouseStatus & { ok: boolean }> {
  return parseJson(
    await ceApi("/api/companies-house/settings", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "Could not save Companies House settings",
  );
}

export async function searchCompaniesHouse(
  query: string,
  opts?: { items_per_page?: number; start_index?: number },
): Promise<CompanySearchResult> {
  const params = new URLSearchParams({
    q: query,
    items_per_page: String(opts?.items_per_page ?? 20),
    start_index: String(opts?.start_index ?? 0),
  });
  return parseJson(
    await ceApi(`/api/companies-house/search?${params}`),
    "Companies House search failed",
  );
}

export async function fetchCompanyProfile(companyNumber: string): Promise<CompanyProfile> {
  const encoded = encodeURIComponent(companyNumber);
  return parseJson(
    await ceApi(`/api/companies-house/company/${encoded}`),
    "Could not load company profile",
  );
}
