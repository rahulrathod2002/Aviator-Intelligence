import { spawnSync, spawn } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const frontendDir = join(root, "frontend");
const captureDir = join(root, "capture");
const venvPython = join(captureDir, ".venv", "Scripts", "python.exe");
const requirementsPath = join(captureDir, "requirements.txt");
const requirementsStamp = join(captureDir, ".venv", ".requirements.sha");

function run(cmd, args, cwd) {
  const result = spawnSync(cmd, args, { stdio: "inherit", cwd, shell: true });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function ensureNodeDeps(dir) {
  if (!existsSync(join(dir, "node_modules"))) {
    run("npm", ["install"], dir);
  }
}

function ensureVenv() {
  if (!existsSync(venvPython)) {
    run("python", ["-m", "venv", ".venv"], captureDir);
  }
  const requirements = readFileSync(requirementsPath, "utf8");
  const hash = createHash("sha256").update(requirements).digest("hex");
  const existing = existsSync(requirementsStamp) ? readFileSync(requirementsStamp, "utf8").trim() : "";
  if (hash !== existing) {
    run(venvPython, ["-m", "pip", "install", "-r", "requirements.txt"], captureDir);
    writeFileSync(requirementsStamp, hash);
  }
}

ensureNodeDeps(frontendDir);
ensureVenv();

const processes = [
  spawn("npm", ["run", "dev"], { stdio: "inherit", cwd: frontendDir, shell: true }),
  spawn(venvPython, ["main.py"], { stdio: "inherit", cwd: captureDir, shell: true })
];

processes.forEach((proc) => {
  proc.on("exit", (code) => {
    if (code && code !== 0) {
      process.exit(code);
    }
  });
});
