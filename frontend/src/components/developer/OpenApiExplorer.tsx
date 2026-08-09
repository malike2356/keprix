"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { alpha, useTheme, type Theme } from "@mui/material/styles";
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

/** Swagger overrides driven by the live MUI palette (no forced hex islands). */
function swaggerThemeSx(theme: Theme) {
  const isDark = theme.palette.mode === "dark";
  const text = theme.palette.text.primary;
  const muted = theme.palette.text.secondary;
  const surface = theme.palette.background.paper;
  const surfaceAlt = theme.palette.background.default;
  const border = theme.palette.divider;
  const link = theme.palette.primary.main;
  const success = theme.palette.success.main;
  const info = theme.palette.info.main;
  const warning = theme.palette.warning.main;
  const error = theme.palette.error.main;
  const verbAlpha = isDark ? 0.18 : 0.1;

  return {
    fontFamily: "inherit",
    color: text,
    "& .info .title, & .info li, & .info p, & .info table, & .info a": {
      color: `${text} !important`,
    },
    "& .info .title small": {
      background: alpha(theme.palette.primary.main, isDark ? 0.16 : 0.08),
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
      borderColor: `${success} !important`,
      color: `${success} !important`,
    },
    "& .btn.authorize svg": {
      fill: `${success} !important`,
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
      color: `${theme.palette.common.white} !important`,
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
      background: `${alpha(info, verbAlpha)} !important`,
      borderColor: `${info} !important`,
    },
    "& .opblock.opblock-post": {
      background: `${alpha(success, verbAlpha)} !important`,
      borderColor: `${success} !important`,
    },
    "& .opblock.opblock-put, & .opblock.opblock-patch": {
      background: `${alpha(warning, verbAlpha)} !important`,
      borderColor: `${warning} !important`,
    },
    "& .opblock.opblock-delete": {
      background: `${alpha(error, verbAlpha)} !important`,
      borderColor: `${error} !important`,
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
      background: `${surface} !important`,
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
          "& .swagger-ui": swaggerThemeSx(theme),
        }}
      />
    </Box>
  );
}
