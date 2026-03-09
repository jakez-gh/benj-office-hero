#!/bin/bash
# Office Hero Mobile App — Emulator Testing Helper

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Office Hero Mobile App Testing ===${NC}\n"

# Check if emulator is running
echo "Checking emulator status..."
ANDROID_HOME="${ANDROID_HOME:=$HOME/Library/Android/sdk}"
if [ ! -d "$ANDROID_HOME" ]; then
  ANDROID_HOME="C:/Users/jake/AppData/Local/Android/Sdk"
fi

DEVICES=$("$ANDROID_HOME/platform-tools/adb" devices 2>&1 | grep "device$" | wc -l)

if [ "$DEVICES" -eq 0 ]; then
  echo -e "${YELLOW}No emulator detected. Starting Samsung_A15...${NC}"
  "$ANDROID_HOME/emulator/emulator" -avd Samsung_A15 -no-snapshot-load &
  sleep 30
  echo -e "${GREEN}Emulator should be starting...${NC}"
else
  echo -e "${GREEN}Emulator detected and online${NC}"
fi

# Check device connection
echo "Verifying ADB connection..."
"$ANDROID_HOME/platform-tools/adb" devices

echo -e "\n${BLUE}=== Starting Expo Dev Server ===${NC}\n"
cd apps/tech-mobile

echo "Cleaning old metro cache..."
rm -rf /tmp/metro-cache 2>/dev/null || true

echo -e "\n${YELLOW}Starting Expo server...${NC}"
echo "When the QR code appears, scan it with Expo Go app on the emulator"
echo "To exit, press Ctrl+C\n"

pnpm start

echo -e "\n${GREEN}Testing complete!${NC}"
