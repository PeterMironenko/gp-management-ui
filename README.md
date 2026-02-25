Building and packaging the application

**1.** Install: 
```sh
/Users/amironenko/git/my/peter/gp-management-ui/.venv/bin/python -m pip install --upgrade pip pyinstaller
```

**2.** Build:
```sh
/Users/amironenko/git/my/peter/gp-management-ui/.venv/bin/python -m PyInstaller --noconfirm --clean --windowed --name gp-management-ui main.py
```

Entry script detected: main.py

Output created in: dist (plus gp-management-ui.spec)

2) Create Installers

**macOS (.dmg)**: 
```sh
brew install create-dmg
```
then
```sh
create-dmg --overwrite "dist/gp-management-ui.dmg" "dist/gp-management-ui.app"
```
For end users: sign + notarize with Apple Developer ID.

**Windows (.exe installer)**: 
use Inno Setup (iscc) with source folder dist\gp-management-ui\* into {app}.

**Debian (.deb)**:
Create package tree: pkg/DEBIAN/control, pkg/usr/lib/gp-management-ui/..., desktop file + icon.
Build with 
```sh
dpkg-deb --build pkg gp-management-ui_1.0.0_amd64.deb.
```
3) Recommended Automation

Use GitHub Actions matrix (macos-latest, windows-latest, ubuntu-latest) to produce .dmg, .exe installer, .deb on every release.