# see https://github.com/albertz/chromehacking for more background

import sys
print >>sys.stderr, "init in install_web_apps.py", sys.argv
if sys.argv[1] != "com.google.Chrome":
	print >>sys.stderr, "exiting, not Chrome"	
	sys.exit()

import sys, time, os, os.path, traceback

# do that global and right here so that we don't loose __file__ later on
myscript = __file__
if os.path.islink(myscript): myscript = os.readlink(myscript)
sys.path.append(os.path.dirname(myscript)) # so we can import from there

import objc
NSObject = objc.lookUpClass("NSObject")
NSAutoreleasePool = objc.lookUpClass("NSAutoreleasePool")
NSScriptCommand = objc.lookUpClass("NSScriptCommand")
NSThread = objc.lookUpClass("NSThread")
NSWindow = objc.lookUpClass("NSWindow")
app = objc.lookUpClass("NSApplication").sharedApplication()
_NSThemeCloseWidget = objc.lookUpClass("_NSThemeCloseWidget")
NSMenuItem = objc.lookUpClass("NSMenuItem")
HoverCloseButton = objc.lookUpClass("HoverCloseButton")
AppController = objc.lookUpClass("AppController")
BrowserCrApplication = objc.lookUpClass("BrowserCrApplication")

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

def isMainThread(): return NSThread.isMainThread()

def do_in_mainthread(f, wait=True):
	if isMainThread(): return f()
	helper = PyAsyncCallHelper.alloc().initWithArgs_(f)
	helper.performSelectorOnMainThread_withObject_waitUntilDone_(helper.call_, None, wait)
	return helper.ret

def do_in_otherthread(f):
	import threading
	class ThreadWorker(threading.Thread):
		def __init__(self):
			super(ThreadWorker, self).__init__()
			self.setDaemon(True)
		def run(self):
			f()
	worker = ThreadWorker()
	worker.start()
	return # we cannot wait, otherwise we would block the current thread and make the whole threading senseless

def fsbrowse(obj):
	objc.lookUpClass("FSInterpreter").interpreter().browse_(obj)
	
FramedBrowserWindow = objc.lookUpClass("FramedBrowserWindow")
BrowserWindowController = objc.lookUpClass("BrowserWindowController")
TabStripController = objc.lookUpClass("TabStripController")
WindowAppleScript = objc.lookUpClass("WindowAppleScript")

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

def openPopupWindow(url):
	if isMainThread():
		do_in_otherthread(lambda: openPopupWindow(url))
		return
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
	for _ in xrange(10):
		w = find_window()
		if w is not None: break
		time.sleep(1)
		# just try again
	assert w is not None
	do_in_mainthread(lambda: w.tabs()[0].setURL_(url))
	return w

def make_dock_icon(title, webappid, url):
	import os.path
	appdir = os.path.expanduser("~/Library/Application Support/ChromeWebApps/Apps")
	try: os.makedirs(appdir)
	except: pass
	
	def filterStdChars(c):
		if c.isdigit(): return True
		if c.isalpha(): return True
		return False
	def filterFilenameChars(c):
		if filterStdChars(c): return True
		if c in " ._-": return True
		return False
	def filterBundleNameChars(c):
		if filterStdChars(c): return True
		if c in " _-": return True
		return False
	def filterBundleIdentifierChars(c):
		if filterStdChars(c): return True
		return False
	def getAppPath(appname): return appdir + "/" + appname + ".app"
	
	appname = "".join(filter(filterFilenameChars, title))
	if appname == "": appname = "Unnamed website"
	if os.path.exists(getAppPath(appname)):
		import itertools
		for i in itertools.count(2):
			newappname = appname + " " + str(i)
			if not os.path.exists(getAppPath(newappname)):
				appname = newappname
				break
	apppath = getAppPath(appname)
	bundleName = "".join(filter(filterBundleNameChars, title))
	bundleIdentifier = "org.ChromeWebApps." + "".join(filter(filterBundleIdentifierChars, title))
	
	scriptfn = os.path.dirname(myscript) + "/dockicon.py"
	
	from createAppBundle import createAppBundle
	createAppBundle(apppath, scriptfn, {
		"CFBundleName": bundleName,
		"CFBundleIdentifier": bundleIdentifier,
		"WebAppURL": url,
		"WebAppId": webappid
		})
	
	from subprocess import Popen, PIPE, STDOUT
	Popen(["open", apppath])

def find_close_widget(w):
	if isinstance(w, WindowAppleScript): w = w.nativeHandle()
	contentView = w.contentView()
	grayFrame = contentView.superview()
	for i in range(len(grayFrame.subviews())):
		v = grayFrame.subviews()[i]
		if isinstance(v, _NSThemeCloseWidget):
			return v, i, grayFrame

try:
	class CustomCloseWidget(_NSThemeCloseWidget):
		pass
except:
	CustomCloseWidget = objc.lookUpClass("CustomCloseWidget")
	
def replace_close_widget(w, clazz=CustomCloseWidget):
	def act():
		v, i, grayFrame = find_close_widget(w)
		newv = clazz.alloc().init()
		newv.retain()
		grayFrame.subviews()[i] = newv
	do_in_mainthread(act)

_close_callbacks_objsnet = {} # any id -> list of ids
close_callbacks = {} # FramedBrowserWindow id -> callback
def _close_callbacks_objsnet_list(w):
	return [w, w.delegate(), w.delegate().tabStripController()]
def install_close_callback(w, callback):
	objsnet_list = _close_callbacks_objsnet_list(w)
	for o in objsnet_list:
		close_callbacks[o] = callback
		_close_callbacks_objsnet[o] = objsnet_list
def remove_close_callback(_o):
	objsnet_list = _close_callbacks_objsnet[_o]
	for o in objsnet_list:
		del close_callbacks[o]
		del _close_callbacks_objsnet[o]
def check_close_callback(o):
	if o in close_callbacks:
		callback = close_callbacks[o]
		print "close callback:", callback
		ret = callback()
		if not ret: return False
		print "really closing"
		remove_close_callback(o)
	return True

def visibleBrowserWindows():
	ws = app.appleScriptWindows()
	ws = [ w for w in ws if w.nativeHandle().isVisible() ]
	return ws

# copied from objc.signature to avoid warning
def my_signature(signature, **kw):
    from objc._objc import selector
    kw['signature'] = signature
    def makeSignature(func):
        return selector(func, **kw)
    return makeSignature

appTerminateSig = "v12@0:4@8"
class BrowserCrApplication(objc.Category(BrowserCrApplication)):
	@my_signature(appTerminateSig)
	def myTerminate_(self, sender):
		try: print "myTerminate_", self, sender
		except: pass
		self.myTerminate_(sender) # this is no recursion when we exchanged the methods

appShouldHandleReopenSig = "c16@0:4@8c12"
class AppController(objc.Category(AppController)):
	@my_signature(appShouldHandleReopenSig)
	def myApplicationShouldHandleReopen_hasVisibleWindows_(self, app, flag):
		try: print "myApplicationShouldHandleReopen", self, app, flag
		except: pass
		flag = flag and bool(visibleBrowserWindows()) # overwrite
		return self.myApplicationShouldHandleReopen_hasVisibleWindows_(app, flag) # this is no recursion when we exchanged the methods
	
performCloseSig = "v12@0:4@8" # FramedBrowserWindow.performClose_
class FramedBrowserWindow(objc.Category(FramedBrowserWindow)):
	@my_signature(performCloseSig)
	def performClose_(self, sender):
		print "myPerformClose", self, sender
		#capi_backtrace()
		if not check_close_callback(self): return
		NSWindow.performClose_(self, sender)

windowWillCloseSig = "c12@0:4@8" # BrowserWindowController.windowWillClose_.signature
commandDispatchSig = "v12@0:4@8"
class BrowserWindowController(objc.Category(BrowserWindowController)):
	@my_signature(windowWillCloseSig)
	def myWindowShouldClose_(self, sender):
		print "myWindowShouldClose", self, sender
		if not check_close_callback(self): return objc.NO
		return self.myWindowShouldClose_(sender) # this is no recursion when we exchanged the methods

	@my_signature(commandDispatchSig)
	def myCommandDispatch_(self, cmd):
		try: sys.stdout.write("myCommandDispatch_ %s %s %s\n" % (self, cmd, cmd.tag()))
		except: pass # like <type 'exceptions.UnicodeEncodeError'>: 'ascii' codec can't encode character u'\u2026' in position 37: ordinal not in range(128)
		if cmd.tag() == 34015: # IDC_CLOSE_TAB
			if not check_close_callback(self): return
		self.myCommandDispatch_(cmd)

closeTabSig = "c12@0:4@8" # TabStripController.closeTab_.signature
commandDispatchForContrSig = "v16@0:4i8@12" # TabStripController.commandDispatch_forController_.signature
class TabStripController(objc.Category(TabStripController)):
	@my_signature(closeTabSig)
	def myCloseTab_(self, sender):
		print "myCloseTab", self, sender
		if not check_close_callback(self): return
		self.myCloseTab_(sender) # this is no recursion when we exchanged the methods

	@my_signature(commandDispatchForContrSig)
	def myCommandDispatch_forController_(self, cmd, controller):
		try: print "myCommandDispatch_forController_", self, cmd, controller
		except: pass # like <type 'exceptions.UnicodeEncodeError'>: 'ascii' codec can't encode character u'\u2026' in position 37: ordinal not in range(128)
		self.myCommandDispatch_forController_(cmd, controller)
	
from ctypes import *
capi = pythonapi

# id objc_getClass(const char *name)
capi.objc_getClass.restype = c_void_p
capi.objc_getClass.argtypes = [c_char_p]

# SEL sel_registerName(const char *str)
capi.sel_registerName.restype = c_void_p
capi.sel_registerName.argtypes = [c_char_p]

def capi_get_selector(name):
    return c_void_p(capi.sel_registerName(name))

# Method class_getInstanceMethod(Class aClass, SEL aSelector)
# Will also search superclass for implementations.
capi.class_getInstanceMethod.restype = c_void_p
capi.class_getInstanceMethod.argtypes = [c_void_p, c_void_p]

# void method_exchangeImplementations(Method m1, Method m2)
capi.method_exchangeImplementations.restype = None
capi.method_exchangeImplementations.argtypes = [c_void_p, c_void_p]

def method_exchange(className, origSelName, newSelName):
	clazz = capi.objc_getClass(className)
	origMethod = capi.class_getInstanceMethod(clazz, capi_get_selector(origSelName))
	newMethod = capi.class_getInstanceMethod(clazz, capi_get_selector(newSelName))
	capi.method_exchangeImplementations(origMethod, newMethod)
	
def hook_into_windowShouldClose():
	method_exchange("BrowserWindowController", "windowShouldClose:", "myWindowShouldClose:")

def hook_into_closeTab():
	method_exchange("TabStripController", "closeTab:", "myCloseTab:")

def hook_into_commandDispatchForContr():
	method_exchange("TabStripController", "commandDispatch:forController:", "myCommandDispatch:forController:")

def hook_into_commandDispatch():
	method_exchange("BrowserWindowController", "commandDispatch:", "myCommandDispatch:")

def hook_into_appShouldReopen():
	method_exchange("AppController", "applicationShouldHandleReopen:hasVisibleWindows:", "myApplicationShouldHandleReopen:hasVisibleWindows:")

def hook_into_appTerminate():
	method_exchange("BrowserCrApplication", "terminate:", "myTerminate:")

capi.backtrace.restype = c_int
capi.backtrace.argtypes = (c_void_p, c_int)
capi.backtrace_symbols_fd.restype = None
capi.backtrace_symbols_fd.argtypes = (c_void_p, c_int, c_int)

def capi_backtrace():
	N = 100
	tracePtrs = (c_void_p * N)()
	c = capi.backtrace(addressof(tracePtrs), N)
	capi.backtrace_symbols_fd(addressof(tracePtrs), c, sys.stdout.fileno())


sharedScriptSuiteReg = objc.lookUpClass("NSScriptSuiteRegistry").sharedScriptSuiteRegistry()
NSScriptCommandDescription = objc.lookUpClass("NSScriptCommandDescription")
sharedAppleEventMgr = objc.lookUpClass("NSAppleEventManager").sharedAppleEventManager()
NSAppleEventDescriptor = objc.lookUpClass("NSAppleEventDescriptor")

from PyObjCTools.TestSupport import fourcc

def register_scripting():
	cmdDesc = NSScriptCommandDescription.alloc().initWithSuiteName_commandName_dictionary_(
		"Chromium Suite",
		"exec Python",
		{
			"Name": "exec Python",
			"CommandClass": "NSScriptCommand", # default behavior
			"AppleEventCode": "ExPy", # 4-char code
			"AppleEventClassCode": "CrSu",
			"Type": "NSString", # return-type
			"ResultAppleEventCode": "ctxt", # return-type
			"Arguments": {
				#"----": {
				#	"Type": "NSString",
				#	"AppleEventCode": "comm"
				#}
			}
		}
	)
	assert cmdDesc is not None
	sharedScriptSuiteReg.registerCommandDescription_(cmdDesc)

	sharedAppleEventMgr.setEventHandler_andSelector_forEventClass_andEventID_(
		appScriptHandler, appScriptHandler.handleExecPy,
		fourcc("CrSu"), fourcc("ExPy"))
	
def handleExecPy(self, ev, replyEv):
	print "execPython called,",
	cmd = ev.descriptorForKeyword_(fourcc("comm")).stringValue()
	print "cmd:", repr(cmd)
	res = eval(cmd)
	res = unicode(res)
	replyEv.setDescriptor_forKeyword_(NSAppleEventDescriptor.descriptorWithString_(res), fourcc("----"))
	return True

try:
	class AppScriptHandler(NSObject):
		def handleExecPy(self, ev, replyEv):
			try: return handleExecPy(self, ev, replyEv)
			except: traceback.print_exc()
			return
except:
	AppScriptHandler = objc.lookUpClass("AppScriptHandler")
appScriptHandler = AppScriptHandler.alloc().init()

def getActiveUrl():
	frameWins = [ w for w in app.orderedWindows() if isinstance(w, FramedBrowserWindow) and w.isVisible() ]
	if len(frameWins) == 0: return None
	mainWin = frameWins[0]
	for w in app.appleScriptWindows():
		if w.nativeHandle() is mainWin:
			return w.activeTab().URL()

registeredWebApps = {} # webappid -> window

def openWebApp(url, webappid=None):
	if isMainThread():
		# this function is supposed to not run in the main thread
		do_in_otherthread(lambda: openWebApp(url, webappid))
		return
	
	w = openPopupWindow(url)
	
	if webappid is None:
		title = ""
		for _ in xrange(10):
			title = w.activeTab().title()
			if title: break
			time.sleep(1) # wait a bit and try again
		webappid = url + " " + str(time.time())
		make_dock_icon(title, webappid, url)

	w = w.nativeHandle()
	registeredWebApps[webappid] = w
	def w_close_handler():
		# if the dock icon helper app exited, we can close the window
		if not webappid in registeredWebApps:
			remove_close_callback(w)
			return True
		w.setIsVisible_(0)
		return False
	install_close_callback(w, w_close_handler)
	
	w.delegate().activate()
	return w

def make_webapp():
	url = getActiveUrl()
	if not url:
		print >>sys.stderr, "no active URL found"
		return
	openWebApp(url)

def onDockClick(webappid, url):
	if not webappid in registeredWebApps:
		# recreate with that webappid
		openWebApp(url, webappid=webappid)
		return
	w = registeredWebApps[webappid]
	w.setIsVisible_(1)
	w.delegate().activate()

def onDockExit(webappid):
	w = registeredWebApps[webappid]
	remove_close_callback(w)
	del registeredWebApps[webappid]
	w.close()

try:
	class PyMenuHandler(NSObject):
		@my_signature("v12@0:4@8")
		def makeWebapp_(self, sender):
			try: return make_webapp()
			except: traceback.print_exc()
except:
	PyMenuHandler = objc.lookUpClass("PyMenuHandler")
pyMenuHandler = PyMenuHandler.alloc().init()

def install_menu():
	mainMenu = app.mainMenu()
	pyMenu = [ m for m in mainMenu.itemArray() if m.title() == "Python" ][0]
	menuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("make webapp", "makeWebapp:", "")
	menuItem.setTarget_(pyMenuHandler)
	pyMenu.submenu().insertItem_atIndex_(menuItem, 0)
	
# it seems, for openWebApp, we need:
# * hook_into_windowShouldClose, for when we click on the window closebutton
# * hook_into_commandDispatch, for when we use the NSMenu (or key shortcut)
def install_webapp_handlers():
	hook_into_windowShouldClose()
	hook_into_commandDispatch()
	hook_into_appShouldReopen()
	hook_into_appTerminate()
	register_scripting()
	install_menu()
	print >>sys.stderr, "webapp handlers installed"

if __name__ == '__main__':
	install_webapp_handlers()
