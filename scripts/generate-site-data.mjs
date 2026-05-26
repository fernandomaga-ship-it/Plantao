import { readdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const contentRoots = [
  path.join(root, "plantoes"),
  path.join(root, "rotinas"),
];
const output = path.join(root, "assets", "site-data.js");
const ignoredDirectories = new Set(["legacy"]);

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    if (ignoredDirectories.has(entry.name)) continue;

    const absolute = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...await walk(absolute));
      continue;
    }

    if (entry.isFile() && /\.html?$/i.test(entry.name)) {
      files.push(absolute);
    }
  }

  return files;
}

function normalizePath(file) {
  return path.relative(root, file).split(path.sep).join("/");
}

function titleFromPath(filePath) {
  const folder = path.dirname(filePath) === "." ? "" : path.dirname(filePath);
  const basename = path.basename(filePath, path.extname(filePath));
  const source = basename === "index" && folder ? folder.split("/").pop() : basename;

  return source
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function categoryFor(text) {
  const value = text.toLowerCase();
  if (value.includes("rotinas/")) return "rotinas";
  if (value.includes("plantoes/bp") || value.includes("plantoes/8b")) return "uti";
  if (/(uti|intensiv|cti|icu)/.test(value)) return "uti";
  if (/(enfermaria|ward|ala|posto|quarto)/.test(value)) return "enfermaria";
  if (/(centro cir|cirurg|cc|sala)/.test(value)) return "centro-cirurgico";
  return "outros";
}

function categoryLabel(category) {
  return {
    uti: "UTI",
    enfermaria: "Enfermaria",
    "centro-cirurgico": "Centro cirúrgico",
    rotinas: "Rotinas",
    outros: "Outros",
  }[category] || "Outros";
}

function cleanText(value) {
  return value
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function toIsoDate(day, month, year) {
  const dd = String(day).padStart(2, "0");
  const mm = String(month).padStart(2, "0");
  return `${year}-${mm}-${dd}`;
}

function shiftDateFromPath(relativePath) {
  return relativePath.match(/(?:^|\/)(\d{4}-\d{2}-\d{2})(?:\/|$)/)?.[1] || "";
}

function shiftDateFromHtml(html) {
  const patterns = [
    /plant[aã]o[^\d]{0,20}(\d{2})\s*\/\s*(\d{2})\s*\/\s*(\d{4})/i,
    /passagem de plant[aã]o[^\d]{0,20}(\d{2})\s*\/\s*(\d{2})\s*\/\s*(\d{4})/i,
    /(\d{2})\s*\/\s*(\d{2})\s*\/\s*(\d{4})\s*<\/div>/i,
  ];

  for (const pattern of patterns) {
    const match = html.match(pattern);
    if (match) {
      return toIsoDate(match[1], match[2], match[3]);
    }
  }

  return "";
}

function formatDateLabel(isoDate) {
  if (!isoDate) return "";
  const [year, month, day] = isoDate.split("-");
  if (!year || !month || !day) return "";
  return `${day}/${month}/${year}`;
}

function sortPages(left, right) {
  const leftDate = left.shiftDate || "";
  const rightDate = right.shiftDate || "";

  if (leftDate !== rightDate) {
    return rightDate.localeCompare(leftDate, "pt-BR");
  }

  return left.title.localeCompare(right.title, "pt-BR");
}

async function pageData(file) {
  const relativePath = normalizePath(file);
  const html = await readFile(file, "utf8");
  const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const h1Match = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
  const h2Match = html.match(/<h2[^>]*>([\s\S]*?)<\/h2>/i);
  const bedMatch = html.match(/class=["'](?:lb-badge|leito-badge)["'][^>]*>([\s\S]*?)<\/div>/i)
    || html.match(/class=["']badge["'][^>]*>(Leito\s+\d+[\s\S]*?)<\/span>/i);
  const patientMatch = html.match(/class=["'](?:lp|leito-paciente)["'][^>]*>([\s\S]*?)(?:<span|<\/div>)/i)
    || html.match(/class=["']meta["'][^>]*>\s*<strong>([\s\S]*?)<\/strong>/i);
  const bed = cleanText(bedMatch?.[1] || "");
  const patient = cleanText(patientMatch?.[1] || "");
  const title = bed && patient
    ? `${bed} - ${patient}`
    : cleanText(h1Match?.[1] || h2Match?.[1] || titleMatch?.[1] || titleFromPath(relativePath));
  const text = cleanText(html);
  const category = categoryFor(`${relativePath} ${title} ${text.slice(0, 1600)}`);
  const folder = path.dirname(relativePath) === "." ? "" : path.dirname(relativePath);
  const stats = await stat(file);
  const shiftDate = shiftDateFromPath(relativePath) || shiftDateFromHtml(html);

  return {
    title,
    path: relativePath,
    href: encodeURI(relativePath),
    folder,
    category,
    categoryLabel: categoryLabel(category),
    summary: bed && patient
      ? `${patient}. ${text.slice(0, 138)}`
      : text.slice(0, 168) || "Arquivo HTML publicado no GitHub Pages.",
    updated: stats.mtime.toISOString().slice(0, 10),
    shiftDate,
    shiftDateLabel: formatDateLabel(shiftDate),
  };
}

const allFiles = await Promise.all(contentRoots.map((r) => walk(r)));
const files = allFiles.flat().sort((a, b) => a.localeCompare(b, "pt-BR"));
const pages = (await Promise.all(files.map((file) => pageData(file)))).sort(sortPages);
const generatedAt = new Date().toISOString().slice(0, 10);

const source = `window.PLANTAO_DATA = ${JSON.stringify({ generatedAt, pages }, null, 2)};\n`;
await writeFile(output, source, "utf8");
console.log(`Generated ${path.relative(root, output)} with ${pages.length} HTML page(s).`);
