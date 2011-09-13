ChromeWebApps
=============

Turn a website into a native-like app on your Mac.

Warning
-------

Before you follow these steps, beware that this is still highly experimental! Pyjector and SIMBL might break your whole system! ChromeWebApps, too! And it might make Google Chrome unstable or not working anymore!

Installation
------------
* Install SIMBL from [here](https://github.com/albertz/simbl). This patched SIMBL is needed to work around restrictions in Chrome. See details on the project page.
* Install [Pyjector](https://github.com/albertz/Pyjector).
* Git clone (or download) these files somewhere.
* Symlink `install_web_apps.py` into `~/Library/Application Support/Pyjector/StartupScripts/`.
* Restart Google Chrome.

Usage
-----

* In Chrome, browse to some site which you want to turn into an app.
* From the "Python" menu in Chrome, select "make webapp".

-- Albert Zeyer, <http://www.az2000.de>

