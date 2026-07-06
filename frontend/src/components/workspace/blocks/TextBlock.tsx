"use client";

import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import CodeBlock from "@/components/workspace/blocks/CodeBlock";

type TextBlockProps = {
  content: string;
};

export default function TextBlock({ content }: TextBlockProps) {
  return (
    <Box sx={{ "& p": { my: 1 }, "& ul, & ol": { pl: 3, my: 1 } }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const text = String(children).replace(/\n$/, "");
            const match = /language-(\w+)/.exec(className || "");
            if (match) {
              return <CodeBlock language={match[1]} content={text} />;
            }
            return (
              <Box
                component="code"
                sx={{
                  fontFamily: "monospace",
                  bgcolor: "background.paper",
                  px: 0.75,
                  py: 0.25,
                  borderRadius: 1,
                  fontSize: "0.9em",
                }}
                {...props}
              >
                {children}
              </Box>
            );
          },
          table({ children }) {
            return (
              <Table size="small" sx={{ my: 1 }}>
                {children}
              </Table>
            );
          },
          thead({ children }) {
            return <TableHead>{children}</TableHead>;
          },
          tbody({ children }) {
            return <TableBody>{children}</TableBody>;
          },
          tr({ children }) {
            return <TableRow>{children}</TableRow>;
          },
          th({ children }) {
            return <TableCell sx={{ fontWeight: 700 }}>{children}</TableCell>;
          },
          td({ children }) {
            return <TableCell>{children}</TableCell>;
          },
          a({ href, children }) {
            return (
              <Link href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </Link>
            );
          },
          p({ children }) {
            return (
              <Typography variant="body1" component="p">
                {children}
              </Typography>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </Box>
  );
}
