#!/usr/bin/python -Es

from __future__ import print_function
import os
import Xlib

from Xlib import X, display, Xatom

dpy = display.Display()

def loop():
	
	atoms = {}
	wm_active_window = dpy.get_atom('_NET_ACTIVE_WINDOW')

	screens = dpy.screen_count()
	for num in range(screens):
		screen = dpy.screen(num)
		screen.root.change_attributes(event_mask=X.PropertyChangeMask)

	while True:
		ev = dpy.next_event()
		if ev.type == X.PropertyNotify:
			if ev.atom == wm_active_window:
				data = ev.window.get_full_property(ev.atom, 0)
				id = int(data.value.tolist()[0])

				hidden = []
				showed = []
				if id != 0:
					for num in range(screens):
						root = dpy.screen(num).root
						for win in root.get_full_property(dpy.get_atom('_NET_CLIENT_LIST'), 0).value.tolist():
							window = dpy.create_resource_object('window', win)
							if window.get_full_property(dpy.get_atom('_NET_WM_STATE'), Xatom.WINDOW) is None:
								continue
							if dpy.get_atom("_NET_WM_STATE_HIDDEN") in window.get_full_property(dpy.get_atom('_NET_WM_STATE'), 0).value.tolist():
								if not win in hidden:
									hidden.append(win)
							else:
								if not win in showed:
									showed.append(win)
				print("Showed:", showed)
				print("Minimized:", hidden)

if __name__ == '__main__':
	loop()
