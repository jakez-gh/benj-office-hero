#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const semver = require('semver');

// bump patch version for each commit, never backwards
const pkgPath = path.resolve(__dirname, '../package.json');
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
const oldVersion = pkg.version || '0.0.0';
const newVersion = semver.inc(oldVersion, 'patch');

pkg.version = newVersion;
fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n');
console.log(`bumped version ${oldVersion} → ${newVersion}`);

// stage the updated package.json so the version bump is committed
try {
  const { execSync } = require('child_process');
  execSync('git add package.json', { stdio: 'ignore' });
} catch (e) {
  // if git not available, ignore
}
