# Image → DTF

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
