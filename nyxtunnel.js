#!/usr/bin/env node
// nyxtunnel — localtunnel launcher that bypasses the broken openurl dep
// (openurl throws "Unsupported platform: android" on termux, killing the
// official lt binary before the tunnel even starts. the lib itself is fine.)
const port = parseInt(process.argv[2] || "8080", 10);

let localtunnel;
const candidates = [
    "localtunnel",
    "/data/data/com.termux/files/usr/lib/node_modules/localtunnel",
    "/usr/lib/node_modules/localtunnel",
    "/usr/local/lib/node_modules/localtunnel",
];
let loaded = null;
for (const c of candidates) {
    try {
        localtunnel = require(c);
        loaded = c;
        break;
    } catch (e) { /* try next */ }
}

if (!localtunnel) {
    console.error("[nyxtunnel] localtunnel lib not found. run: npm install -g localtunnel");
    process.exit(1);
}

(async () => {
    try {
        const tunnel = await localtunnel({ port: port });
        // keep this exact format — nyxphish parses it
        console.log("your url is: " + tunnel.url);
        tunnel.on("close", () => {
            console.log("[nyxtunnel] tunnel closed");
            process.exit(0);
        });
        tunnel.on("error", (err) => {
            console.error("[nyxtunnel] error: " + err);
        });
    } catch (err) {
        console.error("[nyxtunnel] failed: " + err);
        process.exit(1);
    }
})();
