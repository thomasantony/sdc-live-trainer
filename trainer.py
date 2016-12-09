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
        
