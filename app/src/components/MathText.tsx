import React, { useMemo } from "react";
import katex from "katex";

interface MathTextProps {
  text: string;
  className?: string;
}

/**
 * Renders plain prose mixed with $$display$$ and $inline$ LaTeX expressions using KaTeX.
 * Safely preserves line breaks and falls back gracefully if an expression is malformed.
 */
export const MathText: React.FC<MathTextProps> = ({ text, className = "" }) => {
  const html = useMemo(() => {
    if (!text) return "";
    const escapeHtml = (s: string) =>
      s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\n/g, "<br/>");

    // Tokenize $$...$$ first, then $...$
    const pattern = /(\$\$[\s\S]+?\$\$|\$(?:\\.|[^$\\])+\$)/g;
    let out = "";
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = pattern.exec(text)) !== null) {
      if (match.index > lastIndex) {
        out += escapeHtml(text.slice(lastIndex, match.index));
      }
      const token = match[0];
      const isDisplay = token.startsWith("$$");
      const expr = isDisplay ? token.slice(2, -2).trim() : token.slice(1, -1).trim();
      try {
        out += katex.renderToString(expr, {
          displayMode: isDisplay,
          throwOnError: false,
          strict: false,
        });
      } catch {
        out += escapeHtml(token);
      }
      lastIndex = match.index + token.length;
    }

    if (lastIndex < text.length) {
      out += escapeHtml(text.slice(lastIndex));
    }
    return out;
  }, [text]);

  return (
    <div
      className={`leading-relaxed ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};
