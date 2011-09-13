#!/usr/bin/python

import sys, os, os.path

assert len(sys.argv) > 3

apppath = sys.argv[1]
assert os.path.splitext(apppath)[1] == ".app"

pyfile = sys.argv[2]
assert os.path.isfile(pyfile)

props = eval(sys.argv[3])
assert isinstance(props, dict)
assert "CFBundleIdentifier" in props
assert "CFBundleName" in props
if "CFBundleVersion" not in props: props["CFBundleVersion"] = "1.0.0"
if "CFBundleShortVersionString" not in props: props["CFBundleShortVersionString"] = props["CFBundleName"] + " " + props["CFBundleVersion"]
if "CFBundleGetInfoString" not in props: props["CFBundleGetInfoString"] = props["CFBundleShortVersionString"]

os.mkdir(apppath)
os.mkdir(apppath + "/Contents")
os.mkdir(apppath + "/Contents/MacOS")

f = open(apppath + "/Contents/Info.plist", "w")
f.write("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>English</string>
	<key>CFBundleExecutable</key>
	<string>main.py</string>
	<key>CFBundleIconFile</key>
	<string>app.icns</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleSignature</key>
	<string>????</string>
	<key>NSAppleScriptEnabled</key>
	<string>YES</string>
	<key>NSMainNibFile</key>
	<string>MainMenu</string>
	<key>NSPrincipalClass</key>
	<string>NSApplication</string>""")
for k,v in props.iteritems():
	f.write("""
	<key>%s</key>
	<string>%s</string>""" % (k,v))
f.write("""
</dict>
</plist>
""")
f.close()

f = open(apppath + "/Contents/PkgInfo", "w")
f.write("APPL????")
f.close()

f = open(apppath + "/Contents/MacOS/main.py", "w")
f.write(open(pyfile, "r").read()) # just copy the whole file
f.close()

import stat
oldmode = os.stat(apppath + "/Contents/MacOS/main.py").st_mode
os.chmod(apppath + "/Contents/MacOS/main.py", oldmode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
