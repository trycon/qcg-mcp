import * as esbuild from "esbuild";
import fs from "node:fs";
import path from "node:path";
const root = process.argv[2];
const dir = path.join(root, "packages/blocks/src/blocks/landing");
const stub = {
  name: "stub",
  setup(b) {
    b.onResolve({ filter: /^[^./]|^\.\.?\/.*\.(css|svg|png)$/ }, (a) => (a.kind === "entry-point" ? null : { path: a.path, namespace: "stub" }));
    b.onLoad({ filter: /.*/, namespace: "stub" }, () => ({
      contents: "const h=()=>p;const p=new Proxy(h,{get:(t,k)=>k==='__esModule'?false:k===Symbol.toPrimitive?()=>'':p,apply:()=>p,construct:()=>p});module.exports=p;",
      loader: "js",
    }));
  },
};
const out = {};
for (const d of fs.readdirSync(dir)) {
  const def = path.join(dir, d, "definition.ts");
  if (!fs.existsSync(def)) continue;
  try {
    const r = await esbuild.build({ entryPoints: [def], bundle: true, write: false, platform: "node", format: "cjs", plugins: [stub], loader: { ".md": "text" }, jsx: "automatic", logLevel: "silent" });
    const m = { exports: {} };
    new Function("module", "exports", "require", r.outputFiles[0].text)(m, m.exports, () => ({}));
    const e = m.exports;
    const clean = (v) => JSON.parse(JSON.stringify(v ?? null, (k, x) => (typeof x === "function" || k === "visualIcon" || k === "prefixIcon" || k === "icon" && typeof x === "object" ? undefined : x)));
    const fields = (fs) => (Array.isArray(fs) ? fs.map((f) => ({ id: f.id, path: f.path, kind: f.kind, label: f.label, options: f.options?.map((o) => (typeof o === "string" ? o : o.value)), default: f.default, itemSchema: f.itemSchema ? fields(f.itemSchema) : undefined, showWhen: f.showWhen })) : []);
    out[e.blockType] = clean({ label: e.label, description: e.description, group: e.group, limit: e.limit, canDelete: e.canDelete, allowedInCategories: e.allowedInCategories, allowedInPageTypes: e.allowedInPageTypes, fields: fields(e.fields), defaults: e.defaults, help: e.helpMarkdown ?? null });
  } catch (err) { out[d] = { error: String(err).slice(0, 200) }; }
}
process.stdout.write(JSON.stringify(out, null, 1));
