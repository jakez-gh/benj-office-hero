#!/usr/bin/env node
const kill = require('kill-port');
const { spawn } = require('child_process');

async function main() {
  try {
    await kill(3000, 'tcp');
    await kill(3001, 'tcp');
    console.log('killed ports 3000 and 3001 if running');
  } catch (e) {
    // ignore
  }

  // spawn dev server in detached mode so hook doesn't hang
  const proc = spawn('pnpm', ['dev'], { cwd: process.cwd(), shell: true, detached: true, stdio: 'ignore' });
  proc.unref();
  console.log('launched pnpm dev in background');
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
