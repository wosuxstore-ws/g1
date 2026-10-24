#!/usr/bin/env python3
"""Runs in GitHub Actions right after `flutter create` generates ./android.

It gives the app its name, AdMob app id, a proper launcher icon and a dark
splash screen, so the APK feels like a real product instead of a Flutter demo.
"""
import os
import pathlib
import re

APP_NAME = os.environ.get("APP_NAME", "Block Bloom")
# Google's official TEST AdMob app id. Replace with yours (Settings > Secrets > ADMOB_APP_ID)
ADMOB_APP_ID = os.environ.get("ADMOB_APP_ID", "ca-app-pub-3940256099942544~3347511713")

main = pathlib.Path("android/app/src/main")
res = main / "res"


def edit(path, fn):
    p = pathlib.Path(path)
    if p.exists():
        p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")


def write(path, text):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# 1) AndroidManifest: name, AdMob id, internet permission
def patch_manifest(s):
    s = re.sub(r'android:label="[^"]*"', 'android:label="%s"' % APP_NAME, s, count=1)
    if "gms.ads.APPLICATION_ID" not in s:
        meta = (
            '\n        <meta-data android:name="com.google.android.gms.ads.APPLICATION_ID"'
            ' android:value="%s"/>' % ADMOB_APP_ID
        )
        s = re.sub(r"(<application[^>]*>)", lambda m: m.group(1) + meta, s, count=1)
    if "permission.INTERNET" not in s:
        s = s.replace(
            "<application",
            '<uses-permission android:name="android.permission.INTERNET"/>\n    <application',
            1,
        )
    return s


edit(main / "AndroidManifest.xml", patch_manifest)

# 2) Ads SDK needs a reasonably modern Android: 7.0+ still covers ~97% of phones
for gradle in ("android/app/build.gradle.kts", "android/app/build.gradle"):
    edit(gradle, lambda s: s.replace("flutter.minSdkVersion", "24"))


# 3) Launcher icon: four candy blocks on deep indigo (adaptive icon, Android 8+)
def rounded(x, y, size, r):
    return (
        "M{a},{y} H{b} A{r},{r} 0 0 1 {x2},{c} V{d} A{r},{r} 0 0 1 {b},{y2} "
        "H{a} A{r},{r} 0 0 1 {x},{d} V{c} A{r},{r} 0 0 1 {a},{y} Z"
    ).format(a=x + r, b=x + size - r, x=x, x2=x + size, y=y, y2=y + size, c=y + r, d=y + size - r, r=r)


blocks = [
    ("#FF5A7A", 32, 32),
    ("#FFD93D", 56, 32),
    ("#3CB8FF", 32, 56),
    ("#45D483", 56, 56),
]
paths = "\n".join(
    '    <path android:fillColor="%s" android:pathData="%s"/>' % (col, rounded(x, y, 20, 5))
    for col, x, y in blocks
)
write(
    res / "drawable/ic_launcher_foreground.xml",
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
    '    android:width="108dp" android:height="108dp"\n'
    '    android:viewportWidth="108" android:viewportHeight="108">\n' + paths + "\n</vector>\n",
)
write(
    res / "mipmap-anydpi-v26/ic_launcher.xml",
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
    '    <background android:drawable="@color/ic_launcher_background"/>\n'
    '    <foreground android:drawable="@drawable/ic_launcher_foreground"/>\n'
    '    <monochrome android:drawable="@drawable/ic_launcher_foreground"/>\n'
    "</adaptive-icon>\n",
)
write(
    res / "values/bloom_colors.xml",
    '<?xml version="1.0" encoding="utf-8"?>\n'
    "<resources>\n"
    '    <color name="ic_launcher_background">#FF1B1550</color>\n'
    '    <color name="launch_bg">#FF1B1550</color>\n'
    "</resources>\n",
)

# 4) Dark splash so there is no white flash before the first frame
launch = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<layer-list xmlns:android="http://schemas.android.com/apk/res/android">\n'
    '    <item android:drawable="@color/launch_bg"/>\n'
    "</layer-list>\n"
)
for d in ("drawable", "drawable-v21"):
    if (res / d / "launch_background.xml").exists():
        write(res / d / "launch_background.xml", launch)

splash_item = '\n        <item name="android:windowSplashScreenBackground">@color/launch_bg</item>'
for styles in ("values/styles.xml", "values-night/styles.xml"):
    edit(
        res / styles,
        lambda s: re.sub(r'(<style name="LaunchTheme"[^>]*>)', lambda m: m.group(1) + splash_item, s, count=1),
    )

print("Android project patched: %s" % APP_NAME)
