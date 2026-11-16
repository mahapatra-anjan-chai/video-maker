// The Video maker upload page: a tiny local server (Node built-ins only) that files your inputs into
// videos/<project>/ the way the youtube-edit skill expects, and shows the finished renders.
// Run: npm run ui  ->  http://localhost:4500   (listens on this Mac only)
import { createServer } from "node:http";
import { createReadStream, createWriteStream, existsSync, mkdirSync, readFileSync, readdirSync, renameSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { basename, dirname, extname, join, normalize, resolve, sep } from "node:path";
import { homedir } from "node:os";
import { execFile } from "node:child_process";
import { fileURLToPath } from "node:url";

const PORT = Number(process.env.PORT || 4500);
const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const VIDEOS = join(ROOT, "videos");
const RENDERS = join(homedir(), "Movies", "YouTube Renders");
const INPUT_DIRS = ["raw", "img", "audio", "docs"];

const KIND = {
  raw: ["mp4", "mov", "m4v", "mkv", "webm", "avi", "mts", "mxf", "3gp"],
  img: ["png", "jpg", "jpeg", "gif", "webp", "svg", "heic", "avif"],
  audio: ["mp3", "wav", "m4a", "aac", "aif", "aiff", "flac", "ogg"],
};
const MIME = {
  mp4: "video/mp4", mov: "video/quicktime", m4v: "video/mp4", webm: "video/webm", mp3: "audio/mpeg", wav: "audio/wav",
  m4a: "audio/mp4", png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", gif: "image/gif", webp: "image/webp",
  svg: "image/svg+xml", html: "text/html; charset=utf-8", json: "application/json", txt: "text/plain; charset=utf-8",
  md: "text/plain; charset=utf-8", pdf: "application/pdf",
};

const ext = (name) => extname(name).slice(1).toLowerCase();
const folderFor = (name) => Object.keys(KIND).find((k) => KIND[k].includes(ext(name))) || "docs";
const slugify = (s) => String(s).toLowerCase().normalize("NFKD").replace(/[^\w\s-]/g, "").trim().replace(/[\s_]+/g, "-").replace(/-+/g, "-").slice(0, 60);
const safeName = (s) => basename(String(s)).replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_").slice(0, 180) || "file";

function inside(base, p) {
  const full = resolve(base, normalize(p));
  return full === base || full.startsWith(base + sep) ? full : null;
}
function projectDir(slug) {
  if (!slug || slug !== slugify(slug) || slug.startsWith("_")) return null;
  return join(VIDEOS, slug);
}
function readJSON(p, fallback) {
  try { return JSON.parse(readFileSync(p, "utf8")); } catch { return fallback; }
}
function send(res, code, body, type = "application/json") {
  res.writeHead(code, { "Content-Type": type, "Cache-Control": "no-store" });
  res.end(type === "application/json" ? JSON.stringify(body) : body);
}
function readBody(req) {
  return new Promise((ok, fail) => {
    let s = "";
    req.on("data", (c) => { s += c; if (s.length > 2e6) req.destroy(); });
    req.on("end", () => { try { ok(s ? JSON.parse(s) : {}); } catch (e) { fail(e); } });
    req.on("error", fail);
  });
}
function listFiles(dir, rel = "") {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).filter((d) => !d.name.startsWith(".") && !/\.(part|aborted)$/.test(d.name)).flatMap((d) => {
    const p = join(dir, d.name);
    if (d.isDirectory()) return listFiles(p, join(rel, d.name));
    const st = statSync(p);
    return [{ path: join(rel, d.name), name: d.name, size: st.size, mtime: st.mtimeMs }];
  });
}
function renders(slug) {
  const dir = projectDir(slug);
  const local = existsSync(dir) ? readdirSync(dir).filter((f) => ext(f) === "mp4").map((f) => ({ where: "project", file: f, full: join(dir, f) })) : [];
  const outDir = join(RENDERS, slug);
  const delivered = existsSync(outDir) ? readdirSync(outDir).filter((f) => ext(f) === "mp4").map((f) => ({ where: "renders", file: f, full: join(outDir, f) })) : [];
  return [...delivered, ...local].map((r) => {
    const st = statSync(r.full);
    return { where: r.where, file: r.file, size: st.size, mtime: st.mtimeMs };
  }).sort((a, b) => b.mtime - a.mtime);
}
function project(slug) {
  const dir = projectDir(slug);
  const brief = readJSON(join(dir, "brief.json"), {});
  const scriptPath = join(dir, "script.txt");
  return {
    slug,
    brief: { title: slug, purpose: "", style: "ask", shape: "landscape", notes: "", ...brief },
    script: existsSync(scriptPath) ? readFileSync(scriptPath, "utf8") : "",
    files: INPUT_DIRS.flatMap((d) => listFiles(join(dir, d), d).map((f) => ({ ...f, kind: d }))).sort((a, b) => a.mtime - b.mtime),
    renders: renders(slug),
    duration: videoDuration(dir),                           // for the timeline: storyboard, else the voiceover
    voice: speechSpans(dir),                                // when someone is speaking, from the transcript
    scenes: readJSON(join(dir, "scenes.json"), []),        // the creator's scene cards (this page writes them)
    plan: readJSON(join(dir, "scene-plan.json"), null),     // Claude's reading of them, with stills (the skill writes it)
    music: readJSON(join(dir, "music.json"), null),         // the background score Claude picked (the skill writes it)
  };
}
function videoDuration(dir) {
  const sb = readJSON(join(dir, "storyboard.json"), null), vo = readJSON(join(dir, "voiceover", "voiceover.json"), null);
  return (sb && +sb.duration) || (vo && +vo.duration) || null;
}
function speechSpans(dir) {                                 // words closer than 0.45 s apart join into one span
  let w = readJSON(join(dir, "transcript.json"), null);
  if (!w) return [];
  w = Array.isArray(w) ? w : w.words || [];
  const spans = [];
  for (const x of w) {
    const a = +x.start, b = +x.end;
    if (spans.length && a - spans[spans.length - 1][1] < 0.45) spans[spans.length - 1][1] = b;
    else spans.push([a, b]);
  }
  return spans.map(([a, b]) => [Math.round(a * 100) / 100, Math.round(b * 100) / 100]);
}
// Scene cards: keep each card's "edited" time unless its words or files changed, so the page can tell which cards
// changed after Claude's plan.
function saveScenes(dir, list) {
  if (!Array.isArray(list)) return;
  const old = Object.fromEntries(readJSON(join(dir, "scenes.json"), []).map((s) => [s.id, s]));
  const now = new Date().toISOString();
  const clean = list.slice(0, 100).filter((s) => s && /^s\d{1,4}$/.test(s.id)).map((s) => {
    const card = { id: s.id, when: String(s.when || "").slice(0, 500), what: String(s.what || "").slice(0, 2000),
                   files: (Array.isArray(s.files) ? s.files : []).map(String).filter((f) => INPUT_DIRS.includes(f.split("/")[0])).slice(0, 20) };
    const prev = old[s.id];
    const same = prev && prev.when === card.when && prev.what === card.what && JSON.stringify(prev.files || []) === JSON.stringify(card.files);
    return { ...card, edited: same ? prev.edited || now : now };
  });
  writeFileSync(join(dir, "scenes.json"), JSON.stringify(clean, null, 2) + "\n");
}
function saveBrief(slug, patch) {
  const dir = projectDir(slug);
  const cur = readJSON(join(dir, "brief.json"), {});
  const next = { ...cur };
  for (const k of ["title", "style", "shape", "notes", "music_notes"]) if (k in patch) next[k] = String(patch[k]);
  if ("purpose" in patch && ["personal", "office", ""].includes(patch.purpose)) next.purpose = patch.purpose;   // who the video is for
  if ("scenes" in patch) saveScenes(dir, patch.scenes);
  next.updated = new Date().toISOString();
  if (patch.explicit) next.saved = next.updated;      // the Save project button (autosave only sets "updated")
  next.created = cur.created || next.updated;
  writeFileSync(join(dir, "brief.json"), JSON.stringify(next, null, 2) + "\n");
  if ("script" in patch) {
    const script = String(patch.script);
    const p = join(dir, "script.txt");
    if (script.trim()) writeFileSync(p, script.endsWith("\n") ? script : script + "\n");
    else if (existsSync(p)) moveToTrash(dir, "script.txt");
  }
}
function moveToTrash(dir, rel) {
  const src = inside(dir, rel);
  if (!src || !existsSync(src)) return false;
  const trash = join(dir, ".trash");
  mkdirSync(trash, { recursive: true });
  renameSync(src, join(trash, `${Date.now()}-${basename(src)}`));
  return true;
}
function uniquePath(dir, name) {
  let p = join(dir, name), n = 2;
  const stem = name.slice(0, name.length - extname(name).length), e = extname(name);
  while (existsSync(p)) p = join(dir, `${stem} (${n++})${e}`);
  return p;
}
function serveFile(req, res, full, download = false) {
  if (!full || !existsSync(full) || !statSync(full).isFile()) return send(res, 404, { error: "not found" });
  const size = statSync(full).size, type = MIME[ext(full)] || "application/octet-stream";
  if (download) {
    const name = basename(full);
    res.setHeader("Content-Disposition", `attachment; filename="${name.replace(/[^\x20-\x7e]|"/g, "_")}"; filename*=UTF-8''${encodeURIComponent(name)}`);
  }
  const m = /bytes=(\d*)-(\d*)/.exec(req.headers.range || "");
  if (m) {
    const start = m[1] ? Number(m[1]) : Math.max(0, size - Number(m[2]));
    const end = m[1] && m[2] ? Math.min(Number(m[2]), size - 1) : size - 1;
    res.writeHead(206, { "Content-Type": type, "Content-Length": end - start + 1, "Content-Range": `bytes ${start}-${end}/${size}`, "Accept-Ranges": "bytes" });
    return createReadStream(full, { start, end }).pipe(res);
  }
  res.writeHead(200, { "Content-Type": type, "Content-Length": size, "Accept-Ranges": "bytes" });
  createReadStream(full).pipe(res);
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  const parts = url.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  try {
    if (req.method === "GET" && url.pathname === "/") return serveFile(req, res, join(HERE, "index.html"));
    if (req.method === "GET" && url.pathname === "/light") return serveFile(req, res, join(HERE, "index-light.html"));
    if (req.method === "GET" && parts[0] === "poster" && parts.length >= 4 && parts[2] === "raw") {   // a still from a clip, made once
      const dir = projectDir(parts[1]);
      const src = dir && inside(dir, parts.slice(2).join("/"));
      if (!src || !existsSync(src)) return send(res, 404, { error: "not found" });
      const cache = join(dir, ".cache", "posters");
      mkdirSync(cache, { recursive: true });
      const out = join(cache, createHash("sha1").update(src + statSync(src).mtimeMs).digest("hex") + ".jpg");
      if (!existsSync(out)) await new Promise((ok) => execFile("ffmpeg", ["-v", "error", "-ss", "1", "-i", src, "-frames:v", "1",
        "-vf", "scale=360:-2", "-q:v", "4", "-y", out], () => ok()));
      if (!existsSync(out)) await new Promise((ok) => execFile("ffmpeg", ["-v", "error", "-i", src, "-frames:v", "1",
        "-vf", "scale=360:-2", "-q:v", "4", "-y", out], () => ok()));   // clips shorter than 1 s
      return serveFile(req, res, out);
    }

    if (parts[0] === "api" && parts[1] === "projects") {
      if (parts.length === 2 && req.method === "GET") {
        mkdirSync(VIDEOS, { recursive: true });
        const list = readdirSync(VIDEOS, { withFileTypes: true })
          .filter((d) => d.isDirectory() && !d.name.startsWith("_") && !d.name.startsWith(".") && d.name === slugify(d.name))
          .map((d) => {
            const p = project(d.name);
            return { slug: d.name, title: p.brief.title, purpose: p.brief.purpose || "", files: p.files.length, renders: p.renders.length,
                     updated: Math.max(statSync(join(VIDEOS, d.name)).mtimeMs, ...p.files.map((f) => f.mtime)) };
          })
          .sort((a, b) => b.updated - a.updated);
        return send(res, 200, list);
      }
      if (parts.length === 2 && req.method === "POST") {
        const { title, purpose } = await readBody(req);
        if (!["personal", "office"].includes(purpose)) return send(res, 400, { error: "Say who the video is for: Personal or Office." });
        const slug = slugify(title || "");
        if (!slug) return send(res, 400, { error: "Give the video a name." });
        const dir = projectDir(slug);
        for (const d of INPUT_DIRS) mkdirSync(join(dir, d), { recursive: true });
        if (!existsSync(join(dir, "brief.json"))) saveBrief(slug, { title: String(title).trim(), purpose, style: "ask", shape: "landscape", notes: "" });
        return send(res, 200, project(slug));
      }
      const slug = parts[2], dir = projectDir(slug);
      if (!dir || !existsSync(dir)) return send(res, 404, { error: "No such video." });
      if (parts.length === 3 && req.method === "GET") return send(res, 200, project(slug));
      if (parts[3] === "brief" && req.method === "PUT") { saveBrief(slug, await readBody(req)); return send(res, 200, project(slug)); }
      if (parts[3] === "upload" && req.method === "PUT") {
        const name = safeName(url.searchParams.get("name"));
        const folder = join(dir, folderFor(name));
        mkdirSync(folder, { recursive: true });
        const target = uniquePath(folder, name), part = target + ".part";
        const out = createWriteStream(part);
        req.pipe(out);
        out.on("finish", () => { renameSync(part, target); send(res, 200, { path: target.slice(dir.length + 1) }); });
        out.on("error", (e) => send(res, 500, { error: String(e) }));
        req.on("aborted", () => { out.destroy(); try { renameSync(part, part + ".aborted"); } catch {} });
        return;
      }
      if (parts[3] === "music" && req.method === "PUT") {          // "Use this instead" on a music alternative
        const { use } = await readBody(req);
        const m = readJSON(join(dir, "music.json"), null);
        if (!m) return send(res, 404, { error: "No music picked yet." });
        const pool = [m.chosen, ...(m.alternatives || [])].filter(Boolean);
        const pick = pool.find((t) => t.id === use);
        if (use && !pick) return send(res, 400, { error: "That track isn't one of the options." });
        m.requested = pick && pick.id !== (m.chosen || {}).id ? { id: pick.id, title: pick.title, at: new Date().toISOString() } : null;
        writeFileSync(join(dir, "music.json"), JSON.stringify(m, null, 2) + "\n");
        return send(res, 200, project(slug));
      }
      if (parts[3] === "files" && req.method === "DELETE") {
        const rel = normalize(url.searchParams.get("path") || "");
        if (rel.startsWith("..") || !INPUT_DIRS.includes(rel.split(sep)[0])) return send(res, 400, { error: "Only uploaded files can be removed." });
        return moveToTrash(dir, rel) ? send(res, 200, project(slug)) : send(res, 404, { error: "not found" });
      }
      if (parts[3] === "reveal" && req.method === "POST") {
        const { where, file } = await readBody(req);
        const full = where === "renders" ? inside(join(RENDERS, slug), file) : inside(dir, file);
        if (!full || !existsSync(full)) return send(res, 404, { error: "not found" });
        execFile("open", ["-R", full]);
        return send(res, 200, { ok: true });
      }
    }
    if (req.method === "GET" && parts[0] === "media" && parts.length >= 3) {
      const dir = projectDir(parts[1]);
      return serveFile(req, res, dir && inside(dir, parts.slice(2).join("/")));
    }
    if (req.method === "GET" && parts[0] === "renders" && parts.length === 3) {
      const dir = projectDir(parts[1]);
      return serveFile(req, res, dir && inside(join(RENDERS, parts[1]), parts[2]));
    }
    if (req.method === "GET" && url.pathname === "/cover") {   // Epidemic cover art is 3000 px (~20 MB): fetch once, shrink, cache
      let src;
      try { src = new URL(url.searchParams.get("u") || ""); } catch { return send(res, 400, { error: "bad url" }); }
      if (src.protocol !== "https:" || src.hostname !== "cdn.epidemicsound.com" || !/\.(png|jpe?g)$/i.test(src.pathname)) return send(res, 400, { error: "not a cover" });
      const cache = join(VIDEOS, "_shared", ".cover-cache");
      mkdirSync(cache, { recursive: true });
      const out = join(cache, createHash("sha1").update(src.href).digest("hex") + ".jpg");
      if (!existsSync(out)) {
        const r = await fetch(src.href);
        if (!r.ok) return send(res, 502, { error: "cover fetch failed" });
        const tmp = out + ".src";
        writeFileSync(tmp, Buffer.from(await r.arrayBuffer()));
        await new Promise((ok) => execFile("sips", ["-Z", "160", "-s", "format", "jpeg", tmp, "--out", out], () => ok()));
        try { unlinkSync(tmp); } catch {}
      }
      return serveFile(req, res, out);
    }
    if (req.method === "GET" && parts[0] === "download" && parts.length === 4) {   // /download/<slug>/<renders|project>/<file>
      const dir = projectDir(parts[1]);
      const base = parts[2] === "renders" ? join(RENDERS, parts[1]) : dir;
      const full = dir && ext(parts[3]) === "mp4" ? inside(base, parts[3]) : null;
      return serveFile(req, res, full, true);
    }
    send(res, 404, { error: "not found" });
  } catch (e) {
    send(res, 500, { error: String(e && e.message || e) });
  }
});

server.on("error", (e) => {
  if (e.code === "EADDRINUSE") {
    console.log(`The upload page is already running: open http://localhost:${PORT}`);
    console.log(`(to restart it, stop the old one first: kill $(lsof -tiTCP:${PORT} -sTCP:LISTEN))`);
    process.exit(0);
  }
  throw e;
});
server.listen(PORT, "127.0.0.1", () => console.log(`Video maker upload page: http://localhost:${PORT}`));
