import argparse
import base64
import json

import numpy as np
import socketio
import eventlet
import eventlet.wsgi
import time
from PIL import Image
from PIL import ImageOps
from flask import Flask, render_template
from io import BytesIO
import cv2

from keras.models import model_from_json
from keras.preprocessing.image import img_to_array

import tensorflow as tf
from tensorflow.python.ops import control_flow_ops
tf.python.control_flow_ops = control_flow_ops


sio = socketio.Server()
app = Flask(__name__)
model = None

def roi(img): # For model 5
    img = img[60:140,40:280]
    return cv2.resize(img, (200, 66))

def preprocess_input(img):
    return roi(cv2.cvtColor(img, cv2.COLOR_RGB2YUV))

@sio.on('telemetry')
def telemetry(sid, data):
    # The current steering angle of the car
    steering_angle = data["steering_angle"]
    # The current throttle of the car
    throttle = data["throttle"]
    # The current speed of the car
    speed = data["speed"]
    # The current image from the center camera of the car
    imgString = data["image"]
    image = Image.open(BytesIO(base64.b64decode(imgString)))

    # model >= 5
    x = np.asarray(image, dtype=np.float32)
    image_array = preprocess_input(x)
    transformed_image_array = image_array[None, :, :, :]

    steering_angle = float(model.predict(transformed_image_array, batch_size=1))

    speed = float(speed)

    throttle_max = 1.0
    throttle_min = -1.0
    steering_threshold = 3./25

    # Targets for speed controller
    nominal_set_speed = 20
    steering_set_speed = 20

    K = 0.35   # Proportional gain

    # Slow down for turns
    if abs(steering_angle) > steering_threshold:
        set_speed = steering_set_speed
    else:
        set_speed = nominal_set_speed

    throttle = (set_speed - speed)*K
    throttle = min(throttle_max, throttle)
    throttle = max(throttle_min, throttle)
    # else don't change from previous
    print(steering_angle, throttle)
    send_control(steering_angle, throttle)


@sio.on('connect')
def connect(sid, environ):
    print("connect ", sid)
    send_control(0, 0)


def send_control(steering_angle, throttle):
    sio.emit("steer", data={
    'steering_angle': steering_angle.__str__(),
    'throttle': throttle.__str__()
    }, skip_sid=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Remote Driving')
    parser.add_argument('model', type=str,
    help='Path to model definition json. Model weights should be on the same path.')
    args = parser.parse_args()
    with open(args.model, 'r') as jfile:
        # model = model_from_json(json.load(jfile))
        model = model_from_json(jfile.read())

    model.compile("adam", "mse")
    weights_file = args.model.replace('json', 'h5')
    model.load_weights(weights_file)

    # wrap Flask application with engineio's middleware
    app = socketio.Middleware(sio, app)

    # deploy as an eventlet WSGI server
    eventlet.wsgi.server(eventlet.listen(('', 4567)), app)
