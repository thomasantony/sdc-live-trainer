# def roi(img): # For model 5
#     img = img[60:140,40:280]
#     return cv2.resize(img, (200, 66))
#
# # # model >= 5
# # x = np.asarray(image, dtype=np.float32)
# # image_array = roi(cv2.cvtColor(x, cv2.COLOR_RGB2YUV))
# # transformed_image_array = image_array[None, :, :, :]
# #
# # # This model currently assumes that the features of the model are just the images. Feel free to change this.
# # steering_angle = float(model.predict(transformed_image_array, batch_size=1))
#
# # The driving model currently just outputs a constant throttle. Feel free to edit this.
#
# # Throttle down at higher angles
# # neg throttle if |Steering| > 3.75 deg
# speed = float(speed)
#
# throttle_max = 1.0
# throttle_min = -1.0
# steering_threshold = 4./25
#
# # Targets for speed controller
# # nominal_set_speed = 20
# # steering_set_speed = 15
#
# K = 0.20   # Proportional gain
#
# # Slow down for turns
# # if abs(steering_angle) > steering_threshold:
# #     set_speed = steering_set_speed
# # else:
# #     set_speed = nominal_set_speed
#
# throttle = (self.speed - speed)*K
# throttle = min(throttle_max, throttle)
# throttle = max(throttle_min, throttle)
#
# steering_angle = self.steering_angle
# self.send_control(steering_angle, throttle)


from transitions import Machine

class Trainer(object):
     states = ['stopped', 'autonomous', 'manual', 'training']
     transitions = [
        { 'trigger': 'engage_autopilot', 'source': '*', 'dest': 'autonomous' },
        { 'trigger': 'emergency_stop', 'source': '*', 'dest': 'stopped' },
        { 'trigger': 'override', 'source': ['autonomous', 'stopped'], 'dest': 'manual' },
        { 'trigger': 'start_training', 'source': 'manual', 'dest': 'training' },
        { 'trigger': 'stop_training', 'source': 'training', 'dest': 'manual' },
        { 'trigger': 'ionize', 'source': 'gas', 'dest': 'plasma' }
     ]
     default_config = {
        'target_speed': 10,
        'max_steering_angle': 25.,
     }
     def __init__(self, **kwargs):
        self.m = Machine(model=self, states=self.states,
                    transitions=self.transitions, initial='stopped')
        self.target_speed = kwargs.get('target_speed', self.default_config['target_speed'])
        self.max_steering_angle = kwargs.get('max_steering_angle', self.default_config['max_steering_angle'])

        self.pred_steering = 0.0    # Predicted steering command
        self.cmd_steering = 0.0     # Actual steering command
