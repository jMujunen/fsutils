#!/usr/bin/env python3

# rng_rgb.py - Random RGB color generator

import random

def generate_rgb():
    red = random.randint(0, 255)
    green = random.randint(0, 255)
    blue = random.randint(0, 255)
    return (red, green, blue)

if __name__ == '__main__':
    print(generate_rgb())