import kivy
kivy.require('1.0.9')

from kivy.core.window import Window
from kivy.uix.widget import Widget

class TrainerApp(Widget):
    def __init__(self, **kwargs):
        super(TrainerApp, self).__init__(**kwargs)
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'w':
            print('Up')
        elif keycode[1] == 's':
            print('Down')
        elif keycode[1] == 'up':
            print('Left')
        elif keycode[1] == 'down':
            print('Right')
        return True

if __name__ == '__main__':
    from kivy.base import runTouchApp
    runTouchApp(TrainerApp())
