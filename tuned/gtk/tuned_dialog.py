from gi.repository import Gtk

GLADEUI = '/usr/share/tuned/ui/tuned-gui.glade'

class TunedDialog():

	def __init__(self, msg, yes_button_text, no_button_text):
		self._builder = Gtk.Builder()
		self._builder.add_from_file(GLADEUI)

		self._builder.get_object("labelQuestionYesNoDialog").set_text(msg)
		self._builder.get_object("buttonPositiveYesNoDialog").set_label(
			yes_button_text
		)
		self._builder.get_object("buttonNegativeYesNoDialog").set_label(
			no_button_text
		)

	def run(self):
		val = self._builder.get_object("dialogYesNo").run()
		self._builder.get_object("dialogYesNo").hide()
		return val
