/**
 * Browser-side RFQ file parser.
 * Supports PDF (multi-page) and DOCX.
 * Returns plain text content for forwarding to Claude API.
 */

// ── PDF parsing via PDF.js ─────────────────────────────────────────────────

async function parsePdf(file) {
  // Dynamic import keeps the PDF.js worker out of the initial bundle
  const pdfjsLib = await import('pdfjs-dist');

  // Use the bundled worker — Vite will copy it to dist/assets automatically
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.mjs',
    import.meta.url
  ).href;

  const arrayBuffer = await file.arrayBuffer();
  const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
  const pdf = await loadingTask.promise;

  const pageTexts = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    // Join text items; add newline at the end of each "block" (hasEOL)
    const lineText = content.items
      .map(item => (item.hasEOL ? item.str + '\n' : item.str + ' '))
      .join('')
      .trim();
    if (lineText) pageTexts.push(`--- Page ${i} ---\n${lineText}`);
  }

  return pageTexts.join('\n\n');
}

// ── DOCX parsing via Mammoth ───────────────────────────────────────────────

async function parseDocx(file) {
  const mammoth = await import('mammoth/mammoth.browser');
  const arrayBuffer = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer });
  return result.value || '';
}

// ── Public API ─────────────────────────────────────────────────────────────

/**
 * Parse a File object (PDF or DOCX) and return extracted plain text.
 * Throws an Error with a user-readable message on failure.
 *
 * @param {File} file
 * @returns {Promise<string>} Extracted text content
 */
export async function parseRfqFile(file) {
  const name = file.name.toLowerCase();

  if (name.endsWith('.pdf')) {
    try {
      return await parsePdf(file);
    } catch (e) {
      throw new Error(`Failed to parse PDF: ${e.message}`);
    }
  }

  if (name.endsWith('.docx') || name.endsWith('.doc')) {
    try {
      return await parseDocx(file);
    } catch (e) {
      throw new Error(`Failed to parse Word document: ${e.message}`);
    }
  }

  throw new Error('Unsupported file type. Please upload a PDF or Word (.docx) file.');
}

/**
 * Wrap extracted RFQ text with a file-source marker so claudeApi.js
 * can detect it and adjust the prompt accordingly.
 *
 * @param {string} text  Raw extracted text
 * @param {string} filename  Original filename (for display)
 * @returns {string}
 */
export function wrapRfqText(text, filename) {
  // Truncate to ~20k chars to stay within token budget (~5k tokens)
  const MAX_CHARS = 20000;
  const truncated = text.length > MAX_CHARS
    ? text.slice(0, MAX_CHARS) + '\n\n[... document truncated for length ...]'
    : text;
  return `[RFQ_FILE: ${filename}]\n${truncated}`;
}
