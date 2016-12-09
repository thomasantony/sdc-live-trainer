import sys
import tkinter
import os
from server import ControlServer
from platform import system as platform

import socketio
import eventlet
import eventlet.wsgi
from flask import Flask
from functools import partial

class ManualDriver(object):
    def __init__(self):
        # Control variables
        self.steering_angle = 0
        self.throttle = 0

        # State
        self.speed = 0

        # Parameters
        self.turn_rate = 0.5
        self.steering_limit = 10./25.
        self.centering_torque = 0.01/25.

        # Helper functions
        self.turn_left = partial(self.turn, direction=-1)
        self.turn_right = partial(self.turn, direction=+1)
        self.speed_up = partial(self.speed_control, direction=+1)
        self.slow_down = partial(self.speed_control, direction=-1)

        # Control server for getting data from simulator
        self.control_srv = ControlServer()
        self.control_srv.register_callback(self) # Callback for telemetry

    def init_gui(self):
        # Create the root window
        self.root = tkinter.Tk()
        self.root.geometry('350x75+490+550')
        self.root.title('Manual driver')

        # Create a label with status
        self.status = tkinter.StringVar()
        label = tkinter.Label(self.root, width=350, height=75,
                              textvariable=self.status)
        label.pack(fill=tkinter.BOTH, expand=1)

        # Bind key event handlers
        self.root.bind('<Left>', lambda e: self.turn_left())
        self.root.bind('<Right>', lambda e: self.turn_right())
        self.root.bind('<Up>', lambda e: self.speed_up())
        self.root.bind('<Down>', lambda e: self.slow_down())
        self.root.bind('<Key>', self.keydown)

        self.update_status()

        # Start UI loop
        eventlet.spawn_after(1, self.main_loop)

    def start_server(self):
        self.control_srv.start() # Start server

    def focus_gui(self):
        self.root.focus_force()

        # OSX code for focusing window
        if platform() == 'Darwin':
            os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "python" to true' ''')

    def main_loop(self):
        self.focus_gui()
        while True:
            try:
                self.root.update_idletasks()
                self.root.update()
            except:
                pass
            eventlet.sleep(0.01)

    def update_status(self):
        self.status.set('Speed = %0.2f mph, Steering angle = %0.2f deg' %
                    (self.speed, self.steering_angle*25))

    def keydown(self, event):
        if (event.char == 'q'):
            self.root.destroy()
            os._exit(0) # Sledgehammer
        elif event.char == 'c' or event.char == 'C':
            self.reset_steering()

    def speed_control(self, direction):
        """
        direction = +1 for increase, -1 for decrease
        """
        if self.speed < 25:
            self.speed += direction*1
        self.speed = max(0, self.speed)

        self.update_status()

    def update_throttle(self, data):
        """
        Implements P-controller for speed
        """
        throttle_max = 1.0
        throttle_min = -1.0

        K = 0.25    # Proportional gain

        self.throttle = (self.speed - data['speed'])*K
        self.throttle = min(throttle_max, self.throttle)
        self.throttle = max(throttle_min, self.throttle)

    def update_steering(self, data):
        """
        Implements a simple centering torque for the steering
        """

        if abs(self.steering_angle) < self.centering_torque:
            self.steering_angle = 0.0
        elif self.steering_angle > 0:
            self.steering_angle -= self.centering_torque
        elif self.steering_angle < 0:
            self.steering_angle += self.centering_torque

    def turn(self, direction = None):
        """
        direction = +1 for right, -1 for left
        """
        self.steering_angle += direction*self.turn_rate/25.
        self.steering_angle = max(self.steering_angle, -self.steering_limit)
        self.steering_angle = min(self.steering_angle, +self.steering_limit)

        self.update_status()

    def reset_steering(self):
        self.steering_angle = 0.0
        self.update_status()

    # Callback functions triggered by ControlServer
    def handle_connect(self, sid):
        # Focus window when simulator connects
        self.focus_gui()

    def handle_telemetry(self, data):
        # Send current control variables to simulator
        self.control_srv.send_control(self.steering_angle, self.throttle)

        # Update UI
        self.update_status()

        # Steering dynamics and speed controller
        self.update_steering(data)
        self.update_throttle(data)


if __name__ == '__main__':
    driver = ManualDriver()
    driver.init_gui()
    driver.start_server()
