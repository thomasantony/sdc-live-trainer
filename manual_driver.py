import sys
import tkinter
from drive import Driver

import socketio
import eventlet
import eventlet.wsgi
from flask import Flask

# Create the root window
root = tkinter.Tk()
root.geometry('400x200+100+100')
root.title('Manual driver')

# Create a label with instructions
status = tkinter.StringVar()

label = tkinter.Label(root, width=400, height=300, textvariable=status)
label.pack(fill=tkinter.BOTH, expand=1)
# label.bind('<Key>', key)
label.focus_set()

status.set('Speed = 0 mph, Steering Angle = 0.0 deg')

stopflag = False
def main_loop(root):
    while not stopflag:
        try:
            root.update_idletasks()
            root.update()
        except:
            pass
        eventlet.sleep(0.01)
    exit()

from functools import partial

# Create a keystroke handler
def key(event):
    if (event.char == 'q'):
        stopflag = True
        root.destroy()

    elif event.char >= '0' and event.char <= '9':
        if event.char == '0':
            reset_steering()

def turn(event, direction = None):
    global driver_obj
    driver_obj.turn(direction)
    update_status()

def speed_control(event, direction = None):
    global driver_obj
    driver_obj.change_speed(direction)
    update_status()

def reset_steering():
    driver_obj.steering_angle = 0.0
    update_status()

def update_status():
    global status
    status.set('Speed = %0.2f mph, Steering angle = %0.2f deg' %
                (driver_obj.speed, driver_obj.steering_angle*25))

turn_left = partial(turn, direction=-1)
turn_right = partial(turn, direction=+1)
speed_up = partial(speed_control, direction=+1)
slow_down = partial(speed_control, direction=-1)

root.bind('<Left>', turn_left)
root.bind('<Right>', turn_right)
root.bind('<Up>', speed_up)
root.bind('<Down>', slow_down)
root.bind('<Key>', key)

driver_obj = Driver()
sio = socketio.Server()
driver_obj.sio = sio
sio.register_namespace(driver_obj)
app = socketio.Middleware(sio, Flask(__name__))

eventlet.spawn(main_loop, root)
# deploy as an eventlet WSGI server
eventlet.wsgi.server(eventlet.listen(('', 4567)), app)

# root.after(1000, start_server)
# Hand over to the Tkinter event loop

# root.mainloop()

# Close serial port
# ser.close()
