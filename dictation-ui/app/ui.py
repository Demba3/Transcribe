import PySimpleGUI as sg
import queue

class FloatingWindow:
    """A semi-transparent, always-on-top GUI for dictation."""

    def __init__(self):
        self.window = None
        self.level_meter = None
        self.layout = [
            [
                sg.Button('●', key='-REC-', button_color=('white', 'red'), font=('Helvetica', 20), border_width=0),
                sg.Button('■', key='-STOP-', button_color=('white', 'green'), font=('Helvetica', 20), border_width=0),
                sg.ProgressBar(100, orientation='h', size=(20, 20), key='-LEVEL-', bar_color=('blue', 'grey'))
            ]
        ]
        self.audio_q = queue.Queue()

    def create_window(self):
        """Creates and displays the floating window."""
        sg.theme('DarkGrey')
        self.window = sg.Window(
            'Dictation UI',
            self.layout,
            no_titlebar=True,
            keep_on_top=True,
            grab_anywhere=True,
            alpha_channel=0.8,
            finalize=True,
            location=(sg.Window.get_screen_size()[0] - 400, 50)
        )
        self.level_meter = self.window['-LEVEL-']
        return self.window

    def update_level_meter(self, level):
        """Updates the audio level meter."""
        if self.level_meter:
            self.level_meter.update(level)

    def pulse_record_button(self, recording):
        """Pulses the record button color when recording."""
        if self.window:
            button = self.window['-REC-']
            if recording:
                button.update(button_color=('red', 'white'))
            else:
                button.update(button_color=('white', 'red'))

    def close(self):
        """Closes the window."""
        if self.window:
            self.window.close()
            self.window = None
