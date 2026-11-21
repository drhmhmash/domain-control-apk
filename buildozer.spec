[app]
title = Domain Control
package.name = domaincontrol
package.domain = org.drhm.domaincontrol
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 0.1
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.1,arabic-reshaper,python-bidi,openssl,certifi
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
