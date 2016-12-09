import argparse
import base64
import json

import numpy as np
import socketio
from socketio import Namespace

import eventlet
import eventlet.wsgi
import time
from PIL import Image
from PIL import ImageOps
from flask import Flask, render_template

from io import BytesIO
import cv2

from keras.models import model_from_json
from keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array

import tensorflow as tf
from tensorflow.python.ops import control_flow_ops
tf.python.control_flow_ops = control_flow_ops


turn_rate = 0.5
steering_limit = 10./25.

def roi(img): # For model 5
    img = img[60:140,40:280]
    return cv2.resize(img, (200, 66))

class Driver(Namespace):

    def __init__(self):
        super().__init__()
        self.sio = None
        self.steering_angle = 0
        self.speed = 0

    def start_server(self):
        self.app = socketio.Middleware(sio, Flask(__name__))

        # deploy as an eventlet WSGI server
        eventlet.wsgi.server(eventlet.listen(('', 4567)), self.app)

    def on_telemetry(self, sid, data):
        # The current steering angle of the car
        steering_angle = float(data["steering_angle"])
        # The current throttle of the car
        throttle = data["throttle"]
        # The current speed of the car
        speed = data["speed"]
        # The current image from the center camera of the car
        imgString = data["image"]
        image = Image.open(BytesIO(base64.b64decode(imgString)))

        # # model >= 5
        # x = np.asarray(image, dtype=np.float32)
        # image_array = roi(cv2.cvtColor(x, cv2.COLOR_RGB2YUV))
        # transformed_image_array = image_array[None, :, :, :]
        #
        # # This model currently assumes that the features of the model are just the images. Feel free to change this.
        # steering_angle = float(model.predict(transformed_image_array, batch_size=1))

        # The driving model currently just outputs a constant throttle. Feel free to edit this.

        # Throttle down at higher angles
        # neg throttle if |Steering| > 3.75 deg
        speed = float(speed)

        throttle_max = 1.0
        throttle_min = -1.0
        steering_threshold = 4./25

        # Targets for speed controller
        # nominal_set_speed = 20
        # steering_set_speed = 15

        K = 0.20   # Proportional gain

        # Slow down for turns
        # if abs(steering_angle) > steering_threshold:
        #     set_speed = steering_set_speed
        # else:
        #     set_speed = nominal_set_speed

        throttle = (self.speed - speed)*K
        throttle = min(throttle_max, throttle)
        throttle = max(throttle_min, throttle)

        steering_angle = self.steering_angle
        self.send_control(steering_angle, throttle)

    def on_connect(self, sid, environ):
        print("connect ", sid)
        self.send_control(0, 0)

    def change_speed(self, direction):
        """
        direction = +1 for Increase, -1 for Decrease
        """
        if self.speed < 25:
            self.speed += direction*1

        self.speed = max(0, self.speed)

    def turn(self, direction):
        """
        direction = +1 for Right, -1 for left
        """
        self.steering_angle += direction*turn_rate/25.
        self.steering_angle = max(self.steering_angle, -steering_limit)
        self.steering_angle = min(self.steering_angle, +steering_limit)

    def send_control(self, steering_angle, throttle):
        self.sio.emit("steer", data={
            'steering_angle': steering_angle.__str__(),
            'throttle': throttle.__str__()
        }, skip_sid=True)


# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(description='Remote Driving')
#     parser.add_argument('model', type=str,
#     help='Path to model definition json. Model weights should be on the same path.')
#     args = parser.parse_args()
#     with open(args.model, 'r') as jfile:
#         # model = model_from_json(json.load(jfile))
#         model = model_from_json(jfile.read())
#
#     model.compile("adam", "mse")
#     weights_file = args.model.replace('json', 'h5')
#     model.load_weights(weights_file)

    # wrap Flask application with engineio's middleware
    # app = socketio.Middleware(sio, app)
    #
    # # deploy as an eventlet WSGI server
    # eventlet.wsgi.server(eventlet.listen(('', 4567)), app)
