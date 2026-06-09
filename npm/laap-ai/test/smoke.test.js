/* eslint-disable no-console */
const assert = require("assert");
const { venvBin, LAAP_HOME } = require("../lib/install");

describe("laap-ai install helpers", () => {
    it("exposes the venv layout", () => {
        assert.ok(LAAP_HOME.endsWith(path.sep + "laap" + path.sep + "npm"));
        assert.ok(venvBin("laap").includes(".laap" + path.sep + "npm"));
    });
    it("uses platform-specific venv bin path", () => {
        if (process.platform === "win32") {
            assert.ok(venvBin("laap").endsWith("Scripts\\laap.exe"));
        } else {
            assert.ok(venvBin("laap").endsWith("bin/laap"));
        }
    });
});

const path = require("path");
