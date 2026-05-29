#!/usr/bin/env bash
# One-time setup script — run on a Mac with Xcode and CocoaPods installed.
set -euo pipefail

echo "=== Leap CCTV iOS — one-time project setup ==="

# 1. npm dependencies
echo "→ Installing npm dependencies..."
npm install

# 2. Generate Xcode project
if [ -d "ios" ]; then
  echo "→ ios/ already exists, skipping cap add ios"
else
  echo "→ Generating Xcode project (npx cap add ios)..."
  npx cap add ios
fi

# 3. Copy Swift plugin source files into Xcode project directory
echo "→ Copying Swift plugins..."
cp ios-plugins/*.swift ios/App/App/

# 4. Register plugin files in the .xcodeproj
echo "→ Adding plugins to Xcode project..."
gem install xcodeproj --quiet 2>/dev/null || true
ruby scripts/add_plugins_to_xcode.rb

# 5. Sync web assets from ../android/www
echo "→ Syncing web assets..."
npx cap sync ios

# 6. CocoaPods
echo "→ Installing CocoaPods dependencies..."
cd ios/App
pod install
cd ../..

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "  • Open in Xcode:          open ios/App/App.xcworkspace"
echo "  • Run on connected device: npx cap run ios"
echo "  • Build from Xcode and distribute via TestFlight or Ad-hoc"
