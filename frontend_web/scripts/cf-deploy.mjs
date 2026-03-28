import { cpSync, copyFileSync } from "fs";
import { execSync } from "child_process";

// 커밋 해시만 사용 (한글/이모지 포함된 메시지는 Cloudflare API가 거부)
const commitHash = (() => {
  try { return execSync("git rev-parse --short HEAD").toString().trim(); } catch { return "unknown"; }
})();

const src = ".open-next";
const dest = ".open-next/assets";

// worker.js → assets/_worker.js
copyFileSync(`${src}/worker.js`, `${dest}/_worker.js`);
console.log("✓ Copied worker.js → assets/_worker.js");

// _routes.json → assets/_routes.json (정적파일을 Worker 거치지 않고 CDN에서 직접 서빙)
try {
  copyFileSync("_routes.json", `${dest}/_routes.json`);
  console.log("✓ Copied _routes.json → assets/_routes.json");
} catch {
  console.log("⚠ _routes.json not found, skipping");
}

// worker가 상대 경로로 참조하는 디렉터리들을 assets/ 안으로 복사
for (const dir of ["cloudflare", "middleware", "server-functions", ".build"]) {
  try {
    cpSync(`${src}/${dir}`, `${dest}/${dir}`, { recursive: true });
    console.log(`✓ Copied ${dir}/ → assets/${dir}/`);
  } catch {
    // 없는 디렉터리는 스킵
  }
}

console.log("\n🚀 Running wrangler pages deploy...\n");
execSync(`npx wrangler pages deploy .open-next/assets --commit-dirty=true --commit-message="${commitHash}"`, { stdio: "inherit" });
