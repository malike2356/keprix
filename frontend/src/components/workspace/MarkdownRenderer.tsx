"use client";

import TextBlock from "@/components/workspace/blocks/TextBlock";

type MarkdownRendererProps = {
  content: string;
};

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return <TextBlock content={content} />;
}
