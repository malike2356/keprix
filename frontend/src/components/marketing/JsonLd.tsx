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
        "Self-hosted AI agent OS with tools, playbooks, memory, and governance. Community Edition is free (BYOK). Run the workspace on your machine with keprix dashboard; keprixai.com is marketing and docs only.",
      url: "https://keprixai.com",
      downloadUrl: "https://github.com/malike2356/keprix",
      installUrl: "https://keprixai.com/install.json",
      license: "https://opensource.org/licenses/MIT",
      isAccessibleForFree: true,
      offers: [
        {
          "@type": "Offer",
          name: "Community",
          price: 0,
          priceCurrency: "GBP",
          availability: "https://schema.org/InStock",
          url: "https://keprixai.com/pricing",
        },
      ],
      provider: {
        "@type": "Organization",
        name: "Verlox Ltd",
        url: "https://verlox.uk",
        email: "billing@verlox.uk",
      },
    },
    {
      "@type": "Product",
      "@id": "https://keprixai.com/#product",
      name: "Keprix",
      description:
        "Self-hosted AI agent OS with tools, playbooks, memory, and governance. Community Edition is free (BYOK).",
      brand: { "@type": "Brand", name: "Keprix" },
      category: "AI agent operating system",
      url: "https://keprixai.com",
      offers: [
        {
          "@type": "Offer",
          name: "Community",
          price: 0,
          priceCurrency: "GBP",
          availability: "https://schema.org/InStock",
        },
      ],
    },
    {
      "@type": "WebAPI",
      "@id": "https://keprixai.com/guide/reference/api/#webapi",
      name: "Keprix HTTP API",
      description: "OpenAPI-described Keprix agent OS HTTP API on your self-hosted instance",
      documentation: "https://keprixai.com/guide/reference/api/",
      url: "https://keprixai.com/guide/reference/api/",
      provider: {
        "@type": "Organization",
        name: "Verlox Ltd",
        url: "https://verlox.uk",
      },
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
