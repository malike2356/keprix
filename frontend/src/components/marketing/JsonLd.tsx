import Script from "next/script";

/** Embedded schema.org graph for public marketing pages (non-removable for crawlers). */
const PRODUCT_JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      "@id": "https://keprixai.com/#software",
      name: "Keprix",
      applicationCategory: "DeveloperApplication",
      applicationSubCategory: "AI agent operating system",
      operatingSystem: "Linux, macOS, Windows (Docker)",
      description:
        "Open-source, self-hosted AI agent OS for research and building: tools, playbooks, memory, and governance. MIT licensed (BYOK). Run on your machine; keprixai.com is docs and project site only.",
      url: "https://keprixai.com",
      downloadUrl: "https://github.com/malike2356/keprix",
      installUrl: "https://keprixai.com/install.json",
      license: "https://opensource.org/licenses/MIT",
      isAccessibleForFree: true,
    },
    {
      "@type": "SoftwareSourceCode",
      "@id": "https://github.com/malike2356/keprix#code",
      name: "Keprix",
      description:
        "Open-source self-hosted AI agent OS with tools, playbooks, memory, and human-approved self-coding.",
      codeRepository: "https://github.com/malike2356/keprix",
      license: "https://opensource.org/licenses/MIT",
      programmingLanguage: ["Python", "TypeScript"],
      url: "https://github.com/malike2356/keprix",
    },
    {
      "@type": "WebAPI",
      "@id": "https://keprixai.com/guide/reference/api/#webapi",
      name: "Keprix HTTP API",
      description: "OpenAPI-described Keprix agent OS HTTP API on your self-hosted instance",
      documentation: "https://keprixai.com/guide/reference/api/",
      url: "https://keprixai.com/guide/reference/api/",
    },
  ],
};

export default function JsonLd() {
  return (
    <Script
      id="keprix-product-jsonld"
      type="application/ld+json"
      strategy="beforeInteractive"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(PRODUCT_JSON_LD) }}
    />
  );
}
