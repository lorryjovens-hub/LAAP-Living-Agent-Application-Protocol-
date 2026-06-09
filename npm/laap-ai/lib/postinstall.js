#!/usr/bin/env node
/* eslint-disable no-console */
/**
 * npm postinstall hook — pre-warms the LAAP venv so the first `laap` call
 * doesn't have to download anything. Runs in the background with a short
 * timeout so a slow postinstall never blocks `npm install -g`.
 */

const { ensureLaap } = require("./install");

(async () => {
    const TIMEOUT_MS = Number(process.env.LAAP_POSTINSTALL_TIMEOUT_MS || 120000);
    const timer = setTimeout(() => {
        console.error("[laap-ai] postinstall: install timed out, will retry on first run.");
        process.exit(0);
    }, TIMEOUT_MS);
    timer.unref();

    try {
        await ensureLaap();
    } catch (err) {
        // Don't fail `npm install` if Python is missing on the dev machine.
        // The runtime shim will report a clean error when the user runs `laap`.
        console.error("[laap-ai] postinstall:", err.message);
        if (err.hint) console.error("            ", err.hint);
    } finally {
        clearTimeout(timer);
        process.exit(0);
    }
})();
