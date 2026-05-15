import { readdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const output = path.join(root, "assets", "site-data.js");
const ignored = new Set([".git", "node_modules", ".github", "site-rmc", "site-rmc 2"]);

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    if (ignored.has(entry.name)) continue;
    const absolute = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...await walk(absolute));
    } else if (entry.isFile() && /\.html?$/i.test(entry.name)) {
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
  if (value.includes("plantoes/bp")) return "uti";
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

async function pageData(file) {
  const relativePath = normalizePath(file);
  const html = await readFile(file, "utf8");
  const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const h1Match = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
  const h2Match = html.match(/<h2[^>]*>([\s\S]*?)<\/h2>/i);
  const bedMatch = html.match(/class=["'](?:lb-badge|leito-badge)["'][^>]*>([\s\S]*?)<\/div>/i);
  const patientMatch = html.match(/class=["'](?:lp|leito-paciente)["'][^>]*>([\s\S]*?)(?:<span|<\/div>)/i);
  const bed = cleanText(bedMatch?.[1] || "");
  const patient = cleanText(patientMatch?.[1] || "");
  const title = bed && patient
    ? `${bed} - ${patient}`
    : cleanText(h1Match?.[1] || h2Match?.[1] || titleMatch?.[1] || titleFromPath(relativePath));
  const text = cleanText(html);
  const category = categoryFor(`${relativePath} ${title} ${text.slice(0, 1600)}`);
  const folder = path.dirname(relativePath) === "." ? "" : path.dirname(relativePath);
  const stats = await stat(file);

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
  };
}

const files = (await walk(root))
  .map(normalizePath)
  .filter((file) => file !== "index.html")
  .sort((a, b) => a.localeCompare(b, "pt-BR"));

const pages = await Promise.all(files.map((file) => pageData(path.join(root, file))));
const generatedAt = new Date().toISOString().slice(0, 10);

const source = `window.PLANTAO_DATA = ${JSON.stringify({ generatedAt, pages }, null, 2)};\n`;
await writeFile(output, source, "utf8");
console.log(`Generated ${path.relative(root, output)} with ${pages.length} HTML page(s).`);
