// The dashboard with the mock gateway behind it:  npm run dev:mock
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const run = (args) => spawn(process.execPath, args, { cwd: root, stdio: "inherit" });
const kids = [run(["mock/server.mjs"]), run(["node_modules/vite/bin/vite.js"])];
const stop = () => { for (const k of kids) k.kill(); };
for (const k of kids) k.on("exit", stop);
process.on("SIGINT", () => { stop(); process.exit(0); });
process.on("SIGTERM", () => { stop(); process.exit(0); });
