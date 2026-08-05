"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import * as React from "react";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import { getBackendBaseUrl } from "@/lib/ce-api";

declare global {
  interface Window {
    SwaggerUIBundle?: {
      (config: Record<string, unknown>): unknown;
      presets: { apis: unknown };
    };
    SwaggerUIStandalonePreset?: unknown;
  }
}

const SWAGGER_VERSION = "5.18.2";
const SWAGGER_BASE = `https://unpkg.com/swagger-ui-dist@${SWAGGER_VERSION}`;

function loadStylesheet(href: string): void {
  if (document.querySelector(`link[href="${href}"]`)) {
    return;
  }
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  document.head.appendChild(link);
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.body.appendChild(script);
  });
}

type OpenApiExplorerProps = {
  specUrl?: string;
};

/** High-contrast Swagger overrides for Keprix dark (and light) theme. */
function swaggerThemeSx(mode: "light" | "dark") {
  const isDark = mode === "dark";
  const text = isDark ? "#E8EDF5" : "#1A2332";
  const muted = isDark ? "#B7C2D4" : "#4A5568";
  const surface = isDark ? "#141A24" : "#FFFFFF";
  const surfaceAlt = isDark ? "#1C2433" : "#F7F9FC";
  const border = isDark ? "#2E3A4F" : "#D0D7E2";
  const link = isDark ? "#7EB6FF" : "#1565C0";

  return {
    fontFamily: "inherit",
    color: text,
    "& .info .title, & .info li, & .info p, & .info table, & .info a": {
      color: `${text} !important`,
    },
    "& .info .title small": {
      background: isDark ? "#2A3548" : "#E8EEF7",
      color: `${muted} !important`,
    },
    "& .scheme-container": {
      background: `${surfaceAlt} !important`,
      boxShadow: "none !important",
      borderBottom: `1px solid ${border}`,
    },
    "& .scheme-container .schemes > label": {
      color: `${muted} !important`,
    },
    "& .btn.authorize": {
      background: "transparent !important",
      borderColor: "#2E7D32 !important",
      color: isDark ? "#81C784 !important" : "#2E7D32 !important",
    },
    "& .btn.authorize svg": {
      fill: isDark ? "#81C784 !important" : "#2E7D32 !important",
    },
    "& .opblock-tag": {
      color: `${text} !important`,
      borderBottom: `1px solid ${border} !important`,
    },
    "& .opblock-tag small": {
      color: `${muted} !important`,
    },
    "& .opblock": {
      background: `${surface} !important`,
      borderColor: `${border} !important`,
      boxShadow: "none !important",
    },
    "& .opblock .opblock-summary": {
      borderColor: `${border} !important`,
    },
    "& .opblock .opblock-summary-method": {
      color: "#FFFFFF !important",
      fontWeight: 700,
    },
    "& .opblock .opblock-summary-path, & .opblock .opblock-summary-path__deprecated, & .opblock .opblock-summary-path a, & .opblock .opblock-summary-path span":
      {
        color: `${text} !important`,
        fontWeight: 600,
      },
    "& .opblock .opblock-summary-description": {
      color: `${muted} !important`,
    },
    "& .opblock-summary-control svg": {
      fill: `${text} !important`,
    },
    "& .authorization__btn svg, & .opblock-summary-control .authorization__btn svg": {
      fill: `${muted} !important`,
    },
    "& .opblock.opblock-get": {
      background: isDark ? "rgba(49, 109, 176, 0.18) !important" : "rgba(49, 109, 176, 0.08) !important",
      borderColor: isDark ? "#4A7AB5 !important" : "#61AFFE !important",
    },
    "& .opblock.opblock-post": {
      background: isDark ? "rgba(46, 125, 50, 0.18) !important" : "rgba(46, 125, 50, 0.08) !important",
      borderColor: isDark ? "#4CAF50 !important" : "#49CC90 !important",
    },
    "& .opblock.opblock-put, & .opblock.opblock-patch": {
      background: isDark ? "rgba(230, 162, 60, 0.16) !important" : "rgba(230, 162, 60, 0.08) !important",
      borderColor: isDark ? "#E6A23C !important" : "#FCA130 !important",
    },
    "& .opblock.opblock-delete": {
      background: isDark ? "rgba(211, 47, 47, 0.16) !important" : "rgba(211, 47, 47, 0.08) !important",
      borderColor: isDark ? "#E57373 !important" : "#F93E3E !important",
    },
    "& .opblock-body, & .opblock-section-header, & .parameters-container, & .responses-wrapper, & .opblock-description-wrapper, & .opblock-external-docs-wrapper":
      {
        background: `${surfaceAlt} !important`,
        color: `${text} !important`,
      },
    "& .opblock-section-header h4, & .opblock-section-header label, & table thead tr td, & table thead tr th, & .parameter__name, & .parameter__type, & .response-col_status, & .response-col_description, & .tab li":
      {
        color: `${text} !important`,
      },
    "& .parameter__in, & .parameter__empty_description, & .renderedMarkdown p, & .markdown p, & .markdown li": {
      color: `${muted} !important`,
    },
    "& table tbody tr td": {
      color: `${text} !important`,
      borderColor: `${border} !important`,
    },
    "& .model-box, & .model, & section.models, & section.models.is-open h4, & .model-title, & .prop-type, & .prop-name": {
      color: `${text} !important`,
      background: isDark ? `${surface} !important` : undefined,
    },
    "& section.models": {
      borderColor: `${border} !important`,
    },
    "& .model-toggle::after": {
      background: `${text} !important`,
    },
    "& input, & select, & textarea, & .microlight": {
      background: `${surface} !important`,
      color: `${text} !important`,
      borderColor: `${border} !important`,
    },
    "& .topbar": {
      background: `${surfaceAlt} !important`,
      borderBottom: `1px solid ${border}`,
    },
    "& .topbar .download-url-wrapper input": {
      background: `${surface} !important`,
      color: `${text} !important`,
      borderColor: `${border} !important`,
    },
    "& .topbar a, & a": {
      color: `${link} !important`,
    },
    "& .loading-container .loading::after, & .loading-container .loading::before": {
      borderColor: `${border} transparent transparent !important`,
    },
    "& .filter-container .operation-filter-input": {
      background: `${surface} !important`,
      color: `${text} !important`,
      borderColor: `${border} !important`,
    },
    "& .wrapper": {
      padding: "0 !important",
    },
  };
}

export default function OpenApiExplorer({ specUrl = "/openapi.json" }: OpenApiExplorerProps) {
  const theme = useTheme();
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    async function mountExplorer() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(specUrl, { credentials: "include" });
        if (!response.ok) {
          throw new Error(`OpenAPI spec unavailable (${response.status})`);
        }
        const spec = await response.json();

        loadStylesheet(`${SWAGGER_BASE}/swagger-ui.css`);
        await loadScript(`${SWAGGER_BASE}/swagger-ui-bundle.js`);
        await loadScript(`${SWAGGER_BASE}/swagger-ui-standalone-preset.js`);

        if (cancelled || !containerRef.current) {
          return;
        }

        const bundle = window.SwaggerUIBundle;
        const preset = window.SwaggerUIStandalonePreset;
        if (!bundle || !preset) {
          throw new Error("Swagger UI assets failed to initialize");
        }

        containerRef.current.replaceChildren();
        bundle({
          spec,
          domNode: containerRef.current,
          deepLinking: true,
          presets: [bundle.presets.apis, preset],
          layout: "StandaloneLayout",
        });
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load API explorer");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void mountExplorer();
    return () => {
      cancelled = true;
      containerRef.current?.replaceChildren();
    };
  }, [specUrl]);

  if (error) {
    const backendDocs = `${getBackendBaseUrl()}/docs`;
    return (
      <Alert severity="error">
        {error}. Open the backend explorer directly at{" "}
        <Typography component="a" href={backendDocs} target="_blank" rel="noreferrer" sx={{ fontFamily: "monospace" }}>
          {backendDocs}
        </Typography>
        .
      </Alert>
    );
  }

  return (
    <Box sx={{ position: "relative", minHeight: 480, height: "100%" }}>
      {loading ? <SkeletonDetailPanel fields={5} /> : null}
      <Box
        ref={containerRef}
        sx={{
          minHeight: loading ? 0 : 480,
          height: "100%",
          "& .swagger-ui": swaggerThemeSx(theme.palette.mode),
        }}
      />
    </Box>
  );
}
