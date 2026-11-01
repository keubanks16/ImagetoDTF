#!/bin/sh
# Customizes the generated Xcode project (run on macOS after `npx cap add ios`).
set -e
APP=ios/App/App
PLIST="$APP/Info.plist"
PB=/usr/libexec/PlistBuddy

set_key() { # key type value
  $PB -c "Delete :$1" "$PLIST" 2>/dev/null || true
  $PB -c "Add :$1 $2 $3" "$PLIST"
}

set_key CFBundleDisplayName string "GS DTF"
set_key NSPhotoLibraryUsageDescription string "Pick a design from your photos to turn into a DTF print file."
set_key NSPhotoLibraryAddUsageDescription string "Save your finished DTF PNG to your photo library."
set_key NSCameraUsageDescription string "Take a photo of a design to turn into a DTF print file."
set_key ITSAppUsesNonExemptEncryption bool false

# iPhone only, portrait + landscape, no iPad (avoids needing iPad screenshots)
PBX=ios/App/App.xcodeproj/project.pbxproj
sed -i '' 's/TARGETED_DEVICE_FAMILY = "1,2";/TARGETED_DEVICE_FAMILY = 1;/g' "$PBX"
$PB -c "Delete :UISupportedInterfaceOrientations~ipad" "$PLIST" 2>/dev/null || true

# Minimum iOS 15 (App Store requirement from April 2027)
sed -i '' -E 's/IPHONEOS_DEPLOYMENT_TARGET = [0-9.]+;/IPHONEOS_DEPLOYMENT_TARGET = 15.0;/g' "$PBX"
if [ -f ios/App/Podfile ]; then
  sed -i '' -E "s/platform :ios, '[0-9.]+'/platform :ios, '15.0'/" ios/App/Podfile
fi
if [ -f ios/App/CapApp-SPM/Package.swift ]; then
  sed -i '' -E 's/\.iOS\(\.v1[0-9]\)/.iOS(.v15)/' ios/App/CapApp-SPM/Package.swift
fi

# App icon (single 1024 image) and launch screen
ICONSET="$APP/Assets.xcassets/AppIcon.appiconset"
ICON_FILE=$(ls "$ICONSET"/*.png | head -1)
cp ios-assets/AppIcon-1024.png "$ICON_FILE"
for f in "$APP"/Assets.xcassets/Splash.imageset/*.png; do
  cp ios-assets/splash-2732.png "$f"
done

echo "iOS project customized"
