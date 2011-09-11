# http://dev.chromium.org/developers/design-documents/appmode-mac

# http://www.chromium.org/developers/design-documents
# http://www.chromium.org/developers/design-documents/views-windowing
# http://www.chromium.org/developers/design-documents/chromeviews
# http://www.chromium.org/developers/design-documents/chrome-chromeos-windowing
# http://www.chromium.org/developers/design-documents/browser-window

# http://src.chromium.org/viewvc/chrome/trunk/src/chrome/browser/views/html_dialog_view.cc?revision=43137&view=markup&pathrev=43137
# http://src.chromium.org/viewvc/chrome/trunk/src/chrome/browser/ui/cocoa/
# http://src.chromium.org/viewvc/chrome/trunk/src/chrome/browser/ui/cocoa/themed_window.h?view=markup
# http://src.chromium.org/viewvc/chrome/trunk/src/chrome/browser/ui/cocoa/framed_browser_window.h?view=markup
# http://src.chromium.org/viewvc/chrome/trunk/src/chrome/browser/ui/cocoa/browser_window_controller.h?view=markup
# http://src.chromium.org/viewvc/chrome/trunk/src/chrome/browser/ui/cocoa/browser_window_controller.mm?view=markup

# http://stackoverflow.com/questions/7337986/open-new-window-in-chrome-via-pyobjc-python

# http://pyobjc.sourceforge.net/documentation/pyobjc-core/intro.html

import sys, time

import objc
#from Foundation import NSObject
NSObject = objc.lookUpClass("NSObject")
NSAutoreleasePool = objc.lookUpClass("NSAutoreleasePool")
NSScriptCommand = objc.lookUpClass("NSScriptCommand")
NSThread = objc.lookUpClass("NSThread")
app = objc.lookUpClass("NSApplication").sharedApplication()
FramedBrowserWindow = objc.lookUpClass("FramedBrowserWindow")

#pool = NSAutoreleasePool.alloc().init()

try:
	class PyAsyncCallHelper(NSObject):
		def initWithArgs_(self, f):
			self.f = f
			self.ret = None
			return self
		def call_(self, o):
			self.ret = self.f()
except:
	PyAsyncCallHelper = objc.lookUpClass("PyAsyncCallHelper") # already defined earlier

def do_in_mainthread(f, wait=True):
	helper = PyAsyncCallHelper.alloc().initWithArgs_(f)
	helper.performSelectorOnMainThread_withObject_waitUntilDone_(helper.call_, None, wait)
	return helper.ret

BrowserWindowController = objc.lookUpClass("BrowserWindowController")
#o = BrowserWindowController.alloc()

# http://www.chromium.org/developers/design-documents/applescript
# http://codesearch.google.com/#hfE6470xZHk/chrome/browser/cocoa/applescript/window_applescript.mm&type=cs
# http://src.chromium.org/svn/trunk/src/chrome/browser/ui/cocoa/applescript/window_applescript_test.mm
WindowAppleScript = objc.lookUpClass("WindowAppleScript")

def test():
	print >>sys.__stderr__, "Hello from main thread!"

def test2():
	#o = BrowserWindowController.alloc().initWithBrowser_(None)
	o = WindowAppleScript.alloc().init()
	print >>sys.stdout, "Window", o
	return o

#do_in_mainthread(test)
#o = do_in_mainthread(test2)

def replaceRunCode(ipshell):
	runcodeattr = "run_code" if hasattr(ipshell, "run_code") else "runcode"
	__ipython_orig_runcode = getattr(ipshell, runcodeattr)
	def __ipython_runcode(code_obj):
		return do_in_mainthread(lambda: __ipython_orig_runcode(code_obj))
	setattr(ipshell, runcodeattr, __ipython_runcode)

def message_via_html(title, msg, open_callback):
	import BaseHTTPServer
	class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
		got_callback = False
		def log_message(self, format, *args): pass
		def do_GET(webself):
			if webself.path == "/":
				webself.send_response(200)
				webself.send_header("Content-type", "text/html")
				webself.end_headers()
				import cgi
				webself.wfile.write(
					"<html><head><title>" + cgi.escape(title) + "</title></head>" +
					"<body><pre>" +	cgi.escape(msg) + "</pre></body></html>")
				webself.__class__.got_callback = True
			else:
				webself.send_response(404)
				webself.end_headers()

	import BaseHTTPServer
	httpd = BaseHTTPServer.HTTPServer(("", 0), Handler)
	_,port = httpd.server_address

	url = "http://localhost:%d/" % port
	ret = open_callback(url)

	while not Handler.got_callback:
		httpd.handle_request()
		
	return ret

def isMainThread(): return NSThread.isMainThread()

def browserWindows():
	return [ w for w in app.windows() if isinstance(w, FramedBrowserWindow) ]

def openPopupWindow(url):
	assert not isMainThread()
	def open_window():
		o = WindowAppleScript.alloc().init()
		w = o.nativeHandle()
		w.setIsVisible_(0)
		return o, w
	o, w = do_in_mainthread(open_window)
	def open_callback(url):
		t0 = o.tabs()[0]
		arg = NSScriptCommand.alloc().init()
		arg.setArguments_({"javascript":
			"""
			window.open("%s", "_blank", "toolbar=no,menubar=no,location=no");
			""" % url})
		t0.handlesExecuteJavascriptScriptCommand_(arg)
		return url
	dummyurl = message_via_html("", "", lambda url: do_in_mainthread(lambda: open_callback(url)))
	do_in_mainthread(lambda: w.close())
	def find_window():
		for w in app.appleScriptWindows():
			tabs = list(w.tabs())
			if len(tabs) == 0: continue
			while tabs[0].URL() is None: time.sleep(0.001)				
			if dummyurl == tabs[0].URL(): return w
	w = find_window()
	assert w is not None
	do_in_mainthread(lambda: w.tabs()[0].setURL_(url))
	return w

def make_dock_icon():
	from subprocess import Popen, PIPE, STDOUT
	p = Popen(["python"], stdin=PIPE, stdout=sys.stdout, stderr=STDOUT)
	p.stdin.write(
"""
import os, sys

import objc
from Foundation import *
from AppKit import *
from PyObjCTools import AppHelper

class MyApp(NSApplication):

	def XXfinishLaunching(self):
		print "fooo"
		# Make statusbar item
		statusbar = NSStatusBar.systemStatusBar()
		self.statusitem = statusbar.statusItemWithLength_(NSVariableStatusItemLength)
		self.icon = NSImage.alloc().initByReferencingFile_('icon.png')
		self.icon.setScalesWhenResized_(True)
		self.icon.setSize_((20, 20))
		self.statusitem.setImage_(self.icon)
		
		#make the menu
		self.menubarMenu = NSMenu.alloc().init()
		
		self.menuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Click Me', 'clicked:', '')
		self.menubarMenu.addItem_(self.menuItem)
		
		self.quit = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Quit', 'terminate:', '')
		self.menubarMenu.addItem_(self.quit)
		
		#add menu to statusitem
		self.statusitem.setMenu_(self.menubarMenu)
		self.statusitem.setToolTip_('My App')

		print "baaar"

	def clicked_(self, notification):
		NSLog('clicked!')
	
	def applicationDidFinishLaunching_(self,sender):
	    NSApp.setServicesProvider_(self)
	
	def doString_userData_error_(self,pboard,userData,error):
		pboardString = pboard.stringForType_(NSStringPboardType)
		NSLog(u"%s" % pboardString)
	
	#lookupString_userData_error_ = serviceSelector(lookupString_userData_error_)

def serviceSelector(fn):
    # this is the signature of service selectors
    return objc.selector(fn, signature="v@:@@o^@")


MyApp.sharedApplication()
NSApp().activateIgnoringOtherApps_(True)
#NSApp().finishLaunching()
#NSApp().updateWindows()
NSApp().run()
print "XXX1"
MyApp.run()
print "XXX2"

AppHelper.runEventLoop()
print "XXX3"

#del pool
""")
	p.stdin.close()
	return p
