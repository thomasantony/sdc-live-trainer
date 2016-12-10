"""
Live trainer script for Udacity SDC sim

- Control car with Keras model
- Override with manual control
- Train model during manual control
"""
__author__ = 'Thomas Antony'

import os
import sys
import tkinter
import argparse
import base64
import json
import cv2

import numpy as np
from server import ControlServer
from platform import system as platform

import socketio
import eventlet
import eventlet.wsgi
from flask import Flask
from functools import partial

from keras.models import model_from_json
from keras.optimizers import Adam

class LiveTrainer(object):
    def __init__(self, model):
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

        self.mode = 'auto' # can be 'auto' or 'manual'
        self.is_training = False # Trains model if set to true

        self.model = model
        self.batch_size = 16
        self.current_X = [] # List of images
        self.current_Y = [] # List of steering angles

    def init_gui(self):
        # Create the root window
        self.root = tkinter.Tk()
        self.root.geometry('350x75+490+550')
        self.root.title('Hybrid driver')

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
        mode = 'Autonomous' if self.mode == 'auto' else 'Manual override'
        train_text = 'Training neural net ...' if self.is_training else ''
        self.status.set('Mode: %s\n%s\nSpeed = %0.2f mph, Steering angle = %0.2f deg' %
                    (mode, train_text, self.speed, self.steering_angle*25))

    def keydown(self, event):
        if (event.char == 'q'):
            self.root.destroy()
            os._exit(0) # Sledgehammer
        elif event.char == 'c' or event.char == 'C':
            self.reset_steering()
        elif event.char == 'x' or event.char == 'X':
            if self.mode == 'manual':
                self.is_training = False  # No training in autonomous mode
                self.mode = 'auto'
            else:
                self.mode = 'manual'
        elif event.char == 'z' or event.char == 'Z':
            # Toggle flag (only in manual mode)
            if self.mode == 'manual':
                self.is_training = not self.is_training

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
        Implements a simple centering torque for the manual steering
        """
        if self.mode == 'manual':
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

    def roi(self, img): # For model 5
        return cv2.resize(img[60:140,40:280], (200, 66))

    def preprocess_input(self, img):
        return self.roi(cv2.cvtColor(img, cv2.COLOR_RGB2YUV))

    def predict_steering(self, data):
        x = self.preprocess_input(data['image'])
        x = x[None, :, :, :]    # Extend dimension
        return float(model.predict(x, batch_size=1))

    def save_batch(self, data):
        """
        Saves training data in current batch to disk.
        """
        # TODO: Implement save_batch
        pass

    def train_model(self, model, X_train, y_train):
        h = model.fit(X_train, y_train,
            nb_epoch = 1, verbose=0, batch_size=self.batch_size)
        model.save_weights('./checkpoint.h5')
        print('loss : ',h.history['loss'][-1])
        return model

    def process_data(self, data):
        """
        If current batch is full, train the model, save data and reset cache.
        else just save data into batch
        """
        self.current_X.append(self.preprocess_input(data['image']))
        self.current_Y.append(self.steering_angle)

        if len(self.current_Y) == self.batch_size:
            X_train = np.array(self.current_X)
            y_train = np.array(self.current_Y)

            print('Training model ...')
            self.train_model(self.model, X_train, y_train)

            self.save_batch((X_train, y_train))

            # Reset internal batch
            self.current_X = []
            self.current_Y = []

    # Callback functions triggered by ControlServer
    def handle_connect(self, sid):
        # Focus window when simulator connects
        self.focus_gui()

    def handle_telemetry(self, data):

        if self.mode == 'auto':
            self.steering_angle = self.predict_steering(data)
        elif self.mode == 'manual':
            steering_angle = self.steering_angle

            if self.is_training:
                self.process_data(data)

        # Send current control variables to simulator
        self.control_srv.send_control(self.steering_angle, self.throttle)

        # Update UI
        self.update_status()

        # Steering dynamics and speed controller
        self.update_steering(data)
        self.update_throttle(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Remote Driving')
    parser.add_argument('model', type=str,
        help='Path to model definition json. Model weights should be on the same path.')
    args = parser.parse_args()
    with open(args.model, 'r') as jfile:
        model = model_from_json(jfile.read())

    adam = Adam(lr=0.00001)
    model.compile(adam, "mse")
    weights_file = args.model.replace('json', 'h5')

    if os.path.exists(weights_file):
        model.load_weights(weights_file)

    driver = LiveTrainer(model)
    driver.init_gui()
    driver.start_server()
