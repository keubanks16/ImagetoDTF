# GS Baseball DTF Studio

A single-page web app that turns a design into a print-ready DTF file: a transparent, high-resolution PNG tagged at 300 DPI.

**Live app:** https://keubanks16.github.io/ImagetoDTF/

## What it does
1. **Removes the background.** It finds the background color from the image edges and removes it, then cleans the anti-aliased edge pixels so no white halo is left around the outline.
2. **Fixes white areas.** White prints as white ink, so the app lets you recolor it:
   - **Box**: drag around white text. Every white shape fully inside the box changes to the selected color.
   - **Recolor**: tap a single area to fill it with a color. Shading is kept.
   - **Erase**: tap leftover background (gaps, loops) to make it transparent.
3. **Exports at 300 DPI.** You set the print width in inches. The app upscales the image in smooth 2× steps and sharpens it. It then makes the edges solid (no semi-transparent pixels) and writes 300 DPI into the PNG's `pHYs` chunk.

Everything runs in the browser and nothing is uploaded. There are no dependencies: the whole app is `index.html`.

## iPhone app (App Store)
The same `index.html` is wrapped as a native iPhone app named **GS DTF** with [Capacitor](https://capacitorjs.com) (bundle ID `com.stingerzbaseball.gsdtf`). In the app, images open from Photos, Files or the camera. Saving writes the 300 DPI PNG and opens the share sheet, where you can pick Save to Files or Save Image.

No Mac is needed. The GitHub Actions workflow **iOS build → App Store Connect** builds, signs and uploads the app on a cloud Mac. It needs these repo secrets: `APPLE_TEAM_ID`, `ASC_KEY_ID`, `ASC_ISSUER_ID` and `ASC_KEY_P8`.

- `capacitor.config.json`: app ID, name and colors
- `scripts/build-web.sh`: copies the web app into `www/`
- `scripts/ios-setup.sh`: sets permissions, the icon and launch screen, and iPhone-only mode
- `ios-assets/`: 1024 px app icon and launch screen
- `privacy.html`: privacy policy and support page (needed for the App Store listing)
