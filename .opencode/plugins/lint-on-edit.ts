import { spawnSync } from "node:child_process";
import { appendFileSync, mkdirSync } from "node:fs";
import { join, relative } from "node:path";
import { Plugin } from "@opencode/plugin";

const FOLDERS = [
  "python-teacher",
  "typescript-teacher",
  "React-teacher",
  "go-teacher",
  "Java-teacher",
];
const EXTS = [".py", ".ts", ".tsx", ".js", ".jsx", ".scss", ".go", ".java"];
const MAX = 4000;

/** Ruta relativa si el archivo pertenece a una carpeta con linter. */
function lintable(dir: string, file: string): string | null {
  const rel = relative(dir, file).replaceAll("\\", "/");
  const [folder] = rel.split("/");
  if (!FOLDERS.includes(folder)) return null;
  if (!EXTS.some((ext) => rel.endsWith(ext))) return null;
  return rel;
}

export default Plugin.define({
  id: "teachers.lint-on-edit",
  async setup(ctx) {
    const dir = ctx.location.directory;
    const logPath = join(dir, ".opencode", "lint-plugin.log");
    const log = (line: string): void => {
      mkdirSync(join(dir, ".opencode"), { recursive: true });
      appendFileSync(logPath, `${new Date().toISOString()} ${line}\n`);
    };

    log(`setup version=${ctx.app.version}`);
    await ctx.tool.hook("execute.after", (event) => {
      if (event.status !== "completed") return;
      if (!["write", "edit"].includes(event.tool)) return;

      const input = (event as { input?: { path?: string; filePath?: string } }).input;
      const file = input?.path ?? input?.filePath;
      if (!file) return;
      const rel = lintable(dir, file);
      if (!rel) return;

      const run = spawnSync("python", ["tools/lint.py", "--fast", rel], {
        cwd: dir,
        encoding: "utf8",
        timeout: 60_000,
        shell: false,
      });
      const report = `${run.stdout ?? ""}${run.stderr ?? ""}`.trim();
      log(`lint ${rel} status=${run.status} chars=${report.length}`);
      if (run.status === 0 || !report) return;

      const note = `\n\n[lint --fast · ${rel}]\n${report.slice(0, MAX)}`;
      const result = event.result as {
        output?: string;
        content?: Array<{ type: string; text: string }>;
      };
      event.result = {
        ...result,
        output: `${result.output ?? ""}${note}`,
        content: [...(result.content ?? []), { type: "text", text: note.trim() }],
      };
    });
  },
});
