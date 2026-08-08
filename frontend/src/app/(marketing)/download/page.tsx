import type { Metadata } from "next";
import Link from "next/link";
import manifest from "../../../../public/releases/manifest.json";

export const metadata: Metadata = {
  title: "Download Keprix",
  description: "Verified Keprix Community installers, container images, and source releases.",
};

type Artifact = {
  id: string;
  kind: string;
  platform: string;
  architecture: string;
  filename: string;
  url: string;
  size: number;
  sha256: string;
  signature_url: string;
  sbom_url: string;
  provenance_url: string;
};

function sizeLabel(bytes: number): string {
  if (bytes >= 1_000_000_000) return `${(bytes / 1_000_000_000).toFixed(1)} GB`;
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1_000))} KB`;
}

export default function DownloadPage() {
  const artifacts = manifest.artifacts as Artifact[];
  return (
    <main style={{ maxWidth: 1040, margin: "0 auto", padding: "72px 24px" }}>
      <p style={{ fontWeight: 700, letterSpacing: 1 }}>KEPRIX COMMUNITY</p>
      <h1>Download Keprix</h1>
      <p>
        Install Keprix as a self-hosted personal agent OS or connect it as a sidecar. Downloads are
        shown only after the release pipeline publishes their checksum, signature, SBOM, and provenance.
      </p>

      {artifacts.length === 0 ? (
        <section aria-labelledby="source-install" style={{ marginTop: 40 }}>
          <h2 id="source-install">Stable native packages are not published yet</h2>
          <p>No unverified or placeholder installer is offered. You can use the reviewed source path now:</p>
          <pre style={{ overflowX: "auto", padding: 16, background: "#111827", color: "#f9fafb" }}>
            <code>git clone https://github.com/malike2356/keprix.git{`\n`}cd keprix{`\n`}bash scripts/install.sh</code>
          </pre>
        </section>
      ) : (
        <section aria-labelledby="verified-downloads" style={{ marginTop: 40 }}>
          <h2 id="verified-downloads">Verified release {manifest.version}</h2>
          <div style={{ display: "grid", gap: 16 }}>
            {artifacts.map((artifact) => (
              <article key={artifact.id} style={{ border: "1px solid #d1d5db", borderRadius: 12, padding: 20 }}>
                <h3>{artifact.platform} {artifact.architecture}</h3>
                <p>{artifact.filename} ({sizeLabel(artifact.size)})</p>
                <p><code>SHA256 {artifact.sha256}</code></p>
                <p>
                  <a href={artifact.url}>Download</a>{" | "}
                  <a href={artifact.signature_url}>Signature</a>{" | "}
                  <a href={artifact.sbom_url}>SBOM</a>{" | "}
                  <a href={artifact.provenance_url}>Provenance</a>
                </p>
              </article>
            ))}
          </div>
        </section>
      )}

      <section style={{ marginTop: 40 }}>
        <h2>Other installation paths</h2>
        <ul>
          <li><Link href="/guide/getting-started/install/">Bare metal and terminal guide</Link></li>
          <li><Link href="/guide/getting-started/quickstart/">Docker Compose guide</Link></li>
          <li><a href={manifest.release_notes_url}>Release notes and known issues</a></li>
          <li><a href={manifest.support_url}>Community support</a></li>
        </ul>
      </section>
    </main>
  );
}
