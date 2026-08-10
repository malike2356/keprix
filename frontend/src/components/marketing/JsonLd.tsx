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
        "Self-hosted AI agent OS with tools, playbooks, memory, governance, and optional hosted plans. Community Edition is free (BYOK); hosted Pro starts at 49 GBP/month.",
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
        {
          "@type": "Offer",
          name: "Pro",
          price: 49,
          priceCurrency: "GBP",
          availability: "https://schema.org/InStock",
          url: "https://keprixai.com/pricing",
          priceSpecification: {
            "@type": "UnitPriceSpecification",
            price: 49,
            priceCurrency: "GBP",
            unitText: "month",
          },
        },
        {
          "@type": "Offer",
          name: "Team",
          price: 129,
          priceCurrency: "GBP",
          availability: "https://schema.org/InStock",
          url: "https://keprixai.com/pricing",
          priceSpecification: {
            "@type": "UnitPriceSpecification",
            price: 129,
            priceCurrency: "GBP",
            unitText: "month",
          },
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
        "Self-hosted AI agent OS with tools, playbooks, memory, governance, and optional hosted plans.",
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
        {
          "@type": "Offer",
          name: "Pro",
          price: 49,
          priceCurrency: "GBP",
          availability: "https://schema.org/InStock",
        },
        {
          "@type": "Offer",
          name: "Team",
          price: 129,
          priceCurrency: "GBP",
          availability: "https://schema.org/InStock",
        },
      ],
    },
    {
      "@type": "WebAPI",
      "@id": "https://app.keprixai.com/#webapi",
      name: "Keprix HTTP API",
      description: "OpenAPI-described Keprix agent OS HTTP API",
      documentation: "https://app.keprixai.com/openapi.json",
      url: "https://app.keprixai.com/openapi.json",
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
