/* eslint-disable no-console */
/**
 * npm uninstall hook — clean up the LAAP venv so `npm rm -g laap-ai`
 * fully reverses the install.
 */
const fs = require("fs").promises;
const os = require("os");
const path = require("path");

(async () => {
    const home = path.join(os.homedir(), ".laap", "npm");
    try {
        await fs.rm(home, { recursive: true, force: true });
        console.log("[laap-ai] Removed", home);
    } catch (e) {
        console.error("[laap-ai] Could not remove", home, ":", e.message);
    }
})();
