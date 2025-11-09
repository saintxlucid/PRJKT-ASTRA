# Icon Placeholder

**IMPORTANT**: Add your application icon here!

## Requirements

- **Format**: `.ico` (Windows icon)
- **Filename**: `icon.ico`
- **Recommended Size**: 256x256 pixels
- **Must include**: Multiple resolutions (16x16, 32x32, 48x48, 256x256)

## How to Create

### Option 1: Online Converter
1. Find a PNG/JPG image (square recommended)
2. Go to [ICOConvert](https://icoconvert.com/)
3. Upload your image
4. Download the `.ico` file
5. Save it as `icon.ico` in this folder

### Option 2: GIMP (Free)
1. Open your image in GIMP
2. Scale to 256x256: Image → Scale Image
3. Export as: File → Export As → `icon.ico`
4. Check "Compressed (PNG)" in the export dialog
5. Save in this folder

### Option 3: Photoshop
1. Install [ICO Format Plugin](https://www.telegraphics.com.au/sw/product/ICOFormat)
2. Create 256x256 canvas
3. Save As → `icon.ico`

### Option 4: ImageMagick (Command Line)
```bash
magick convert input.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico
```

## Quick Placeholder

If you don't have an icon yet, download a temporary one:
- [IconArchive - Windows Icons](https://iconarchive.com/tag/windows)
- [Flaticon](https://www.flaticon.com/)
- [Icons8](https://icons8.com/)

## Current Status

⚠️ **No icon found** - The app will use the default Electron icon until you add `icon.ico`.

---

Once added, the icon will appear:
- In the Windows taskbar
- In the system tray
- On the installed application
- In the installer
