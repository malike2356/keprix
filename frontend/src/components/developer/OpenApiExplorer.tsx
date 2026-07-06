"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
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

export default function OpenApiExplorer({ specUrl = "/openapi.json" }: OpenApiExplorerProps) {
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
          "& .swagger-ui": { fontFamily: "inherit" },
        }}
      />
    </Box>
  );
}
