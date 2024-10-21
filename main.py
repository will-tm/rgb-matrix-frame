#!/usr/bin/env python
import os
import sys
import configparser

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from flask import Flask, Response
from threading import Thread
from PIL import Image, ImageEnhance

cwd = os.path.realpath(__file__)
config = configparser.ConfigParser()
config.read("config.ini")
frames = []
should_update_frames = True

if len(sys.argv) < 2:
    image_file = config.get('frame', 'file')
else:
    image_file = sys.argv[1]

gif = Image.open(os.path.join(os.getcwd(), 'gifs', image_file))

try:
    num_frames = gif.n_frames
except Exception:
    sys.exit("provided image is not a gif")

# Status
on = bool(config.get('frame', 'status'))
brightness = int(config.get('frame', 'brightness'))
print(f"RGB Matrix is now {'ON' if on else 'OFF'} with brightness={brightness}%")

# REST API
app = Flask(__name__)

@app.route("/ping")
def ping():
    return "pong"

@app.route("/off")
def off():
    set_matrix(_on=False)
    return Response(status=200)

@app.route("/on")
def on():
    set_matrix(_on=True)
    return Response(status=200)

@app.route("/brightness/<value>")
def set_brightness(value):
    set_matrix(_on=True, _brightness=int(value))
    return Response(status=200)

@app.route("/file/<value>")
def set_file(value):
    config.set('frame', 'file', value)
    with open('config.ini', 'w') as configfile:
        config.write(configfile)
    print(f'GIF set to {image_file}')
    return Response(status=200)

@app.route("/brightness")
def get_brightness():
    return str(brightness)

@app.route("/status")
def status():
    return "1" if on else Response(status=200)

# Configuration for the matrix
options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.gpio_slowdown = 2
options.pixel_mapper_config = "Rotate:270"
options.hardware_mapping = 'adafruit-hat'

matrix = RGBMatrix(options = options)

def set_matrix(_on, _brightness=None):
    global on, brightness, matrix, should_update_frames
    should_update_frames = True
    on = _on
    if _brightness:
        brightness = _brightness
    print(f"RGB Matrix is now {'ON' if on else 'OFF'} with brightness={brightness}%")

    config.set('frame', 'status', str(on))
    config.set('frame', 'brightness', str(brightness))
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def update_frames():
    global frames, num_frames, gif, should_update_frames
    frames = []
    for frame_index in range(0, num_frames):
        gif.seek(frame_index)
        frame = gif.copy()
        frame.thumbnail((matrix.width, matrix.height), Image.NEAREST)
        enhancer = ImageEnhance.Brightness(frame.convert("RGB"))
        frame = enhancer.enhance(brightness/100)                
        frames.append(frame)

    should_update_frames = False
    print('Updated frames for GIF')

# Matrix loop
def rgb_matrix_loop():
    global image_file, num_frames, gif, frames, should_update_frames
    try:
        canvas = matrix.CreateFrameCanvas()

        while(True):
            if image_file != config.get('frame', 'file'):
                image_file = config.get('frame', 'file')
                gif = Image.open(os.path.join(os.getcwd(), 'gifs', image_file))
                try:
                    num_frames = gif.n_frames
                    should_update_frames = True
                    matrix.Clear()
                except Exception:
                    sys.exit("provided image is not a gif")

            if should_update_frames:
                update_frames()

            if on:
                for frame in frames:
                    canvas.SetImage(frame)
                    matrix.SwapOnVSync(canvas, framerate_fraction=4)
            else:
                matrix.Clear()

                
    except KeyboardInterrupt:
        sys.exit(0)

# Start 
Thread(target=rgb_matrix_loop).start()
app.run(host='0.0.0.0', port=8080)
