#!/usr/bin/python -u

# http://codesearch.google.com/#u_9_nDrchrw/pygame-1.7.1release/lib/macosx.py&ct=rc&cd=6&q=GetCurrentProcess%20ApplicationServices%20%20file:.py
# http://codesearch.google.com/#TjZxI4W0_Cw/trunk/cocos/audio/SDL/darwin.py&ct=rc&cd=2&q=GetCurrentProcess%20ApplicationServices%20%20file:.py

import os, os.path, sys, time
from pprint import pprint

bundlePath = os.path.dirname(__file__) + "/../.."

import signal
signal.signal(signal.SIGABRT, lambda *args: os._exit(1))
signal.signal(signal.SIGPIPE, lambda *args: os._exit(1))

from Foundation import *
from AppKit import *
import objc

bundleInfoDict = NSBundle.bundleWithPath_(bundlePath).infoDictionary()
webAppURL = bundleInfoDict["WebAppURL"]
webAppId = bundleInfoDict["WebAppId"]

import aem

chromeApp = None

def connectToChrome():
	global chromeApp
	fullpath = aem.findapp.byname("Google Chrome")
	chromeApp = aem.Application(fullpath)
	
def execPy(cmd, tryToReconnect=False):
	global chromeApp
	if chromeApp is None: connectToChrome()
	try:
		return chromeApp.event("CrSuExPy", {"comm": cmd}).send()
	except:
		if not tryToReconnect: return
		# maybe connection to Chrome was lost. try to reconnect
		chromeApp = None
		connectToChrome()
		time.sleep(2) # wait a bit. Chrome needs to register our AppleEvent first
		return chromeApp.event("CrSuExPy", {"comm": cmd}).send()
		
def openPopupWindow(url):
	execPy("openPopupWindow(%s)" % repr(url))

def onDockClick():
	execPy("onDockClick(%s, %s)" % (repr(webAppId), repr(webAppURL)), tryToReconnect=True)

def onExit():
	execPy("onDockExit(%s)" % repr(webAppId))

def setIcon(baseurl):
	url = NSURL.URLWithString_relativeToURL_("/favicon.ico", NSURL.URLWithString_(baseurl))
	img = NSImage.alloc().initWithContentsOfURL_(url)
	if img is None:
		return
	app.setApplicationIconImage_(img)

class MyAppDelegate(NSObject):
	def applicationShouldHandleReopen_hasVisibleWindows_(self, app, flag):
		try:
			onDockClick()
		except: # eg. sigpipe
			sys.excepthook(*sys.exc_info())
			#os._exit(1)
			
	def applicationDidFinishLaunching_(self, notification):
		menu = NSMenu.alloc().init()
		#menu.addItem_(NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('View Trash', 'view:', ''))
		#menu.addItem_(NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Empty Trash', 'empty:', ''))
		#menu.addItem_(NSMenuItem.separatorItem())
		menu.addItem_(NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Quit', 'terminate:', 'q'))
		
		windowMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Foobar', None, '')
		windowMenuItem.setSubmenu_(menu)
		
		app.setMainMenu_(NSMenu.alloc().init())
		app.mainMenu().addItem_(windowMenuItem)
				
		try: setIcon(webAppURL)
		except: pass
		
		print "Dock icon initialized"
		onDockClick()

	def applicationWillTerminate_(self, sender):
		try:
			onExit()
		except: # eg. sigpipe
			sys.excepthook(*sys.exc_info())
	
	def open_window(self):
		self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
			NSMakeRect(100,50,300,400),
			NSTitledWindowMask | NSMiniaturizableWindowMask | NSResizableWindowMask | NSClosableWindowMask,
			NSBackingStoreBuffered,
			objc.NO)
		self.window.setIsVisible_(True)

app = NSApplication.sharedApplication()
delegate = MyAppDelegate.alloc().init()
app.setDelegate_(delegate)
app.finishLaunching()
app.updateWindows()
#app.activateIgnoringOtherApps_(True)
app.run()
