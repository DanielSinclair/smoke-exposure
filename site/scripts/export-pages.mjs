import { access, cp, mkdir, rm, writeFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "/smoke-exposure";
const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteDirectory = path.resolve(scriptDirectory, "..");
const clientDirectory = path.join(siteDirectory, "dist", "client");
const outputDirectory = path.join(siteDirectory, "pages-dist");
const workerUrl = pathToFileURL(path.join(siteDirectory, "dist", "server", "index.js"));
workerUrl.searchParams.set("pages-export", String(Date.now()));

await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });
await cp(clientDirectory, outputDirectory, { recursive: true });

const { default: worker } = await import(workerUrl.href);
const response = await worker.fetch(
  new Request("https://danielsinclair.github.io/"),
  { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
  { waitUntil() {}, passThroughOnException() {} },
);

if (!response.ok) throw new Error(`Static render failed with status ${response.status}`);

let html = await response.text();
html = html
  // Vinext's server-rendered bootstrap can contain an inline dynamic import in
  // addition to ordinary href/src attributes. Prefix every quoted root asset
  // reference, not just the visible HTML attributes.
  .replaceAll('"/assets/', `"${basePath}/assets/`)
  .replaceAll("'/assets/", `'${basePath}/assets/`)
  .replaceAll("`/assets/", `\`${basePath}/assets/`)
  .replaceAll(
    `http://localhost:3000${basePath}/`,
    `https://danielsinclair.github.io${basePath}/`,
  );

const rootAssetReference = /(?:href|src)=["']\/assets\/|import\(["']\/assets\//;
if (rootAssetReference.test(html)) {
  throw new Error("Static export contains a root-level asset reference");
}

const assetReferences = new Set([
  ...[...html.matchAll(/(?:href|src)="([^"]*\/assets\/[^"]+)"/g)].map((match) => match[1]),
  ...[...html.matchAll(/import\("([^"]*\/assets\/[^"]+)"\)/g)].map((match) => match[1]),
]);

for (const assetReference of assetReferences) {
  const expectedPrefix = `${basePath}/assets/`;
  if (!assetReference.startsWith(expectedPrefix)) {
    throw new Error(`Static export contains an unscoped asset reference: ${assetReference}`);
  }
  const outputRelativePath = assetReference.slice(`${basePath}/`.length);
  await access(path.join(outputDirectory, outputRelativePath));
}

await writeFile(path.join(outputDirectory, "index.html"), html, "utf8");
await writeFile(path.join(outputDirectory, ".nojekyll"), "", "utf8");
console.log(`Exported GitHub Pages site to ${outputDirectory}`);
