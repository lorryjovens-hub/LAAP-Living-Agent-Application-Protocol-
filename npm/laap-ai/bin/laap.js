#!/usr/bin/env node
/* eslint-disable no-console */
/**
 * `laap` command shim — npm wrapper for the LAAP Python CLI.
 *
 * When invoked:
 *   1. Ensures LAAP is installed in an isolated venv at ~/.laap/npm/venv
 *      (no-op if already there; takes ~10s on first run)
 *   2. Spawns the `laap` binary inside that venv, forwarding all args + stdio
 *
 * Usage:
 *   npx laap-ai --version
 *   npx laap-ai -i
 *   npm i -g laap-ai && laap -i
 */

const { ensureLaap } = require("../lib/install");
const { spawn } = require("child_process");

(async () => {
    let laapBin;
    try {
        laapBin = await ensureLaap();
    } catch (err) {
        console.error("[laap-ai]", err.message);
        if (err.hint) console.error("  →", err.hint);
        process.exit(1);
    }
    const child = spawn(laapBin, process.argv.slice(2), {
        stdio: "inherit",
        env: process.env,
    });
    child.on("error", (err) => {
        console.error("[laap-ai] spawn failed:", err.message);
        process.exit(1);
    });
    child.on("exit", (code, signal) => {
        if (signal) {
            // Pass the signal through so Ctrl-C behaves the same.
            process.kill(process.pid, signal);
        } else {
            process.exit(code || 0);
        }
    });
})();
