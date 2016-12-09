import sys
import tkinter
import os
from drive import ControlServer
from platform import system as platform

import socketio
import eventlet
import eventlet.wsgi
from flask import Flask
from functools import partial

class ManualDriver(object):
    def __init__(self, update_cb):
        """
        update_cb: Callback for updating UI
        """
        self.steering_angle = 0
        self.speed = 0
        self.turn_rate = 0.5
        self.steering_limit = 10./25.

        self.turn_left = partial(self.turn, direction=-1)
        self.turn_right = partial(self.turn, direction=+1)
        self.speed_up = partial(self.speed_control, direction=+1)
        self.slow_down = partial(self.speed_control, direction=-1)

        self.update_cb = update_cb

    def speed_control(self, direction):
        """
        direction = +1 for Increase, -1 for Decrease
        """
        if self.speed < 25:
            self.speed += direction*1
        self.speed = max(0, self.speed)

        if self.update_cb is not None:
            self.update_cb(self.steering_angle, self.speed)

    def turn(self, direction = None):
        """
        direction = +1 for Right, -1 for left
        """
        self.steering_angle += direction*self.turn_rate/25.
        self.steering_angle = max(self.steering_angle, -self.steering_limit)
        self.steering_angle = min(self.steering_angle, +self.steering_limit)

        if self.update_cb is not None:
            self.update_cb(self.steering_angle, self.speed)

    def reset_steering(self):
        self.steering_angle = 0.0

        if self.update_cb is not None:
            self.update_cb(self.steering_angle, self.speed)

    def handle_telemetry(self, data, server):
        throttle_max = 1.0
        throttle_min = -1.0

        K = 0.20   # Proportional gain

        throttle = (self.speed - data['speed'])*K
        throttle = min(throttle_max, throttle)
        throttle = max(throttle_min, throttle)

        steering_angle = self.steering_angle
        server.send_control(steering_angle, throttle)

        if self.update_cb is not None:
            self.update_cb(self.steering_angle, self.speed)


def update_status(steering_angle, speed):
    status.set('Speed = %0.2f mph, Steering angle = %0.2f deg' %
                (speed, steering_angle*25))


# Create the root window
root = tkinter.Tk()
root.geometry('400x200+100+100')
root.title('Manual driver')

# Create a label with status
status = tkinter.StringVar()
label = tkinter.Label(root, width=400, height=300, textvariable=status)
label.pack(fill=tkinter.BOTH, expand=1)
label.focus_set()

status.set('Speed = 0 mph, Steering Angle = 0.0 deg')

def main_loop(root):
    root.focus_force()
    if platform() == 'Darwin':  # How Mac OS X is identified by Python
        os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "python" to true' ''')

    while True:
        try:
            root.update_idletasks()
            root.update()
        except:
            pass
        eventlet.sleep(0.01)

# Bind key event handlers
driver = ManualDriver(update_status)

root.bind('<Left>', lambda e: driver.turn_left())
root.bind('<Right>', lambda e: driver.turn_right())
root.bind('<Up>', lambda e: driver.speed_up())
root.bind('<Down>', lambda e: driver.slow_down())

def key(event):
    if (event.char == 'q'):
        root.destroy()
        os._exit(0) # Sledgehammer
    elif event.char == '0':
        driver.reset_steering()

root.bind('<Key>', key)

# Start UI loop
eventlet.spawn_after(1, main_loop, root)

control_srv = ControlServer()
control_srv.register_callback(driver.handle_telemetry) # Callback for telemetry
control_srv.start() # Start server
