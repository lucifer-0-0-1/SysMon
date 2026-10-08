#!/bin/sh
# Build dist/LaptopMonitor-<version>-<arch>.AppImage: runs on any distro with glibc >= 2.34
# (PySide6 wheels' floor: Ubuntu 22.04+, Debian 12+, Fedora 35+, openSUSE Leap 16+...). Bundles Python, PySide6 and psutil.
# Needs: curl, file, and the xcb-util libraries below installed: they're bundled because Qt's X11
# backend needs them and stock desktops often lack some (libxcb-cursor0 especially).
set -eu
cd "$(dirname "$0")/.."
py=3.12
arch=$(uname -m)
version=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' main.py)
build=build/appimage
appdir="$build/AppDir"
rm -rf "$build"
mkdir -p "$build" dist

# Relocatable Python from python-appimage (manylinux), unpacked without FUSE.
# GITHUB_TOKEN (set in CI) lifts the API's 60 requests/hour anonymous limit.
url=$(curl -fsSL --retry 3 ${GITHUB_TOKEN:+--oauth2-bearer $GITHUB_TOKEN} "https://api.github.com/repos/niess/python-appimage/releases/tags/python$py" |
      grep -o "https://[^\"]*manylinux2014_$arch.AppImage" | head -1)
curl -fsSL --retry 3 -o "$build/python.AppImage" "$url"
chmod +x "$build/python.AppImage"
(cd "$build" && ./python.AppImage --appimage-extract >/dev/null && mv squashfs-root AppDir)
rm -rf "$appdir"/AppRun "$appdir"/*.desktop "$appdir"/*.png "$appdir"/.DirIcon "$appdir/usr/share/tcltk"

python="$appdir/opt/python$py/bin/python$py"
"$python" -m pip install -q --no-warn-script-location --no-compile psutil python-dotenv PySide6-Essentials
# Drop Qt parts a widgets app never loads (QML/Quick, translations, dev tools): roughly halves the size
qt="$appdir/opt/python$py/lib/python$py/site-packages/PySide6"
rm -rf "$qt"/Qt/qml "$qt"/Qt/translations "$qt"/Qt/lib/libQt6Quick* "$qt"/Qt/lib/libQt6Qml* \
       "$qt"/Qt/lib/libQt6Designer* "$qt"/Qt/lib/libQt6Pdf* "$qt"/Qt/lib/libQt6ShaderTools* \
       "$qt"/Qt/libexec "$qt"/assistant "$qt"/designer "$qt"/linguist "$qt"/lupdate "$qt"/lrelease \
       "$qt"/qmlformat "$qt"/qmllint "$qt"/qmlls "$qt"/Qt*Quick* "$qt"/QtQml* "$qt"/QtDesigner*

packaging/install-files.sh "$appdir"
# Own directory: usr/lib holds the bundled Python's libssl etc., which must not leak into
# host programs we spawn (nvidia-smi, notify-send) through LD_LIBRARY_PATH
mkdir -p "$appdir/usr/lib/xcb"
for lib in libxcb-cursor.so.0 libxcb-icccm.so.4 libxcb-image.so.0 libxcb-keysyms.so.1 libxcb-render-util.so.0 \
           libxcb-util.so.1; do
    cp -L "$(ldconfig -p | awk -v l="$lib" '$1 == l {print $NF; exit}')" "$appdir/usr/lib/xcb/"
done
cp packaging/laptop-monitor.desktop laptop-monitor.svg "$appdir/"
cat > "$appdir/AppRun" <<APPRUN
#!/bin/sh
here=\$(dirname "\$(readlink -f "\$0")")
export LD_LIBRARY_PATH="\$here/usr/lib/xcb\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
exec "\$here/opt/python$py/bin/python$py" "\$here/usr/share/laptop-monitor/main.py" "\$@"
APPRUN
chmod +x "$appdir/AppRun"

curl -fsSL --retry 3 -o "$build/appimagetool" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$arch.AppImage"
curl -fsSL --retry 3 -o "$build/runtime" \
    "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-$arch"
chmod +x "$build/appimagetool"
ARCH=$arch "$build/appimagetool" --appimage-extract-and-run --no-appstream --runtime-file "$build/runtime" \
    "$appdir" \
    "dist/LaptopMonitor-$version-$arch.AppImage"
