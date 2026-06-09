/* eslint-disable no-console */
/**
 * LAAP installation helper — used by the `laap` shim and postinstall.
 *
 * Strategy:
 *   1. If a `laap` binary is already on PATH, use that.
 *   2. Otherwise, locate a Python 3.10+ interpreter.
 *   3. Create an isolated venv at ~/.laap/npm/venv
 *   4. Install LAAP into that venv (via `uv` if present, else `pip`).
 *
 * All operations are idempotent and cached — re-running is near-instant.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const which = require("which");
const execa = require("execa").execa;

const LAAP_HOME = path.join(os.homedir(), ".laap", "npm");
const VENV_DIR  = path.join(LAAP_HOME, "venv");
const MARKER    = path.join(LAAP_HOME, ".installed");

function venvBin(name) {
    return process.platform === "win32"
        ? path.join(VENV_DIR, "Scripts", `${name}${process.platform === "win32" ? ".exe" : ""}`)
        : path.join(VENV_DIR, "bin", name);
}

function findSystemPython() {
    const candidates = process.platform === "win32"
        ? ["python3", "python", "py"]
        : ["python3", "python"];
    for (const c of candidates) {
        try {
            const found = which.sync(c);
            const { stdout } = require("child_process").spawnSync(
                found, ["-c", "import sys; v=sys.version_info; print('%d.%d'%(v[0],v[1]))"]
            );
            const ver = stdout.toString().trim();
            const [maj, min] = ver.split(".").map(Number);
            if (maj === 3 && min >= 10) return found;
        } catch (_) { /* keep looking */ }
    }
    return null;
}

async function exists(p) {
    try { await fs.promises.access(p, fs.constants.X_OK); return true; }
    catch { return false; }
}

async function ensureLaap(opts = {}) {
    const version = process.env.LAAP_VERSION || "0.3.0";
    const extras  = process.env.LAAP_EXTRAS  || "cli";

    // 0) honour existing global install — most users already have one.
    try {
        const existing = which.sync("laap");
        if (existing) return existing;
    } catch (_) { /* not on PATH yet */ }

    // 1) cached install
    if (await exists(venvBin("laap")) && fs.existsSync(MARKER)) {
        return venvBin("laap");
    }

    if (opts.skipInstall) {
        const err = new Error("LAAP is not installed yet.");
        err.hint = "Re-run without --skip-install, or run `npm i -g laap-ai` to install.";
        throw err;
    }

    // 2) install
    await fs.promises.mkdir(LAAP_HOME, { recursive: true });

    let useUv = false;
    try { which.sync("uv"); useUv = true; } catch (_) { /* no uv */ }

    if (useUv) {
        console.log("[laap-ai] Creating venv with uv...");
        await execa("uv", ["venv", VENV_DIR, "--python", "3.11"]);
        console.log("[laap-ai] Installing laap with uv pip (this takes ~10s)...");
        await execa("uv", [
            "pip", "install", "--python", venvBin("python"),
            `laap[${extras}]==${version}`,
        ]);
    } else {
        const py = findSystemPython();
        if (!py) {
            const err = new Error("Python 3.10+ is required but was not found on PATH.");
            err.hint = "Install Python from https://python.org or `brew install python@3.11`.";
            throw err;
        }
        console.log("[laap-ai] Creating venv with stdlib venv...");
        await execa(py, ["-m", "venv", VENV_DIR]);
        console.log("[laap-ai] Installing laap with pip (this takes ~15s)...");
        await execa(venvBin("python"), [
            "-m", "pip", "install", "--upgrade", "pip",
        ]);
        await execa(venvBin("python"), [
            "-m", "pip", "install", `laap[${extras}]==${version}`,
        ]);
    }

    await fs.promises.writeFile(MARKER, new Date().toISOString());
    console.log("[laap-ai] LAAP installed into", LAAP_HOME);
    return venvBin("laap");
}

module.exports = { ensureLaap, venvBin, LAAP_HOME, VENV_DIR };
