#!/usr/bin/env python

import os
import sys
import mmap
import struct
import optparse

#prescale values from datasheet
prescal_map={
    0b0000: 120,
    0b0001: 180,
    0b0010: 240,
    0b0011: 360,
    0b0100: 480,
    0b1000: 12000,
    0b1001: 24000,
    0b1010: 36000,
    0b1011: 48000,
    0b1100: 72000,
    0b1111: 1}

class PWM(object):
    def __init__(self, freq=1000):
        self.is_run=0
        self.calc_params( freq)
        self.prescal_config()

    def reset_params(self, freq):
        self.calc_params( freq)
        self.prescal_config()
        if self.is_run:
            self.run()

    def calc_params(self, freq):
        self.prescal=-1
        for prsc in prescal_map.keys():
            if (self.prescal<0 or 24000000/prescal_map[prsc]/freq-200<delta) and 24000000/prescal_map[prsc]/freq-200>=0:
                 delta = 24000000/prescal_map[prsc]/freq-200
                 self.prescal=prsc
        if self.prescal==-1:
            self.prescal=15
        self.interval_ticks = 24000000//prescal_map[self.prescal]//freq

    def set_duty(self, duty):
        self.duty_ticks=duty*self.interval_ticks//100
        if self.is_run:
            self.run()
                 
    def prescal_config(self):

        f = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)

        pwm_mem = mmap.mmap(f, 0x1000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=0x01C21000)
        data = self.prescal
        pwm_mem.seek(0x400,0)
        pwm_mem.write(struct.pack('I', data))

    def run(self):

        self.is_run=1
        f = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)

        #config PA5 as PWM out
        pin_mem = mmap.mmap(f, 0x1000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=0x01C20000)
        pin_mem.seek(0x800,0)
        data=(struct.unpack('I', pin_mem.read(4))[0])
        data = data | (0b0011 << 20)
        data = data & ~(0b0001 << 22)
        pin_mem.seek(0x800,0)
        pin_mem.write(struct.pack('I', data))

        #enable PWM
        pwm_mem = mmap.mmap(f, 0x1000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=0x01C21000)
        pwm_mem.seek(0x400,0)
        data=(struct.unpack('I', pwm_mem.read(4))[0])
        data = data | 0b0111<<4
        pwm_mem.seek(0x400,0)
        pwm_mem.write(struct.pack('I', data))

        #set PWM period
        pwm_mem.seek(0x404,0)
        cycle_data=self.interval_ticks<<16 | self.duty_ticks
        pwm_mem.write(struct.pack('I', cycle_data))

    def stop(self):

        self.is_run=0
        f = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)

        #config PA5 as GPIO out and set 0
        pin_mem = mmap.mmap(f, 0x1000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=0x01C20000)
        pin_mem.seek(0x800,0)
        data=(struct.unpack('I', pin_mem.read(4))[0])
        data = data | (0b0001 << 20)
        data = data & ~(0b0011 << 21)
        pin_mem.seek(0x800,0)
        pin_mem.write(struct.pack('I', data))
        #set 0 value
        pin_mem.seek(0x810,0)
        data=(struct.unpack('I', pin_mem.read(4))[0])
        data = data & ~(0b0001 << 5)
        pin_mem.seek(0x810,0)
        pin_mem.write(struct.pack('I', data))

        #disable PWM
        pwm_mem = mmap.mmap(f, 0x1000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=0x01C21000)
        pwm_mem.seek(0x400,0)
        data=(struct.unpack('I', pwm_mem.read(4))[0])
        data = data & ~(0b0111<<4)
        pwm_mem.seek(0x400,0)
        pwm_mem.write(struct.pack('I', data))



def main():

    parser = optparse.OptionParser()

    parser.add_option("-f", "--frequency", dest="freq", metavar="FREQUENCY",
            type=int, help="frequency of PWM", default=1000)

    parser.add_option("-d", "--duty", dest="duty", help="duty of PWM - percentage value",
            nargs=1, type=int, metavar="DUTY", default=50)

    parser.add_option("-r", "--run", action="store_true", dest="run",
            help="start the PWM")

    parser.add_option("-s", "--stop", action="store_true", dest="stop",
            help="stop the PWM")

    (options, args) = parser.parse_args()

    if options.run is not None and options.stop is not None:
        parser.print_help()
        print "\nError: Both run and stop are specified"
        return -1
    elif options.run is None and options.stop is None:
        parser.print_help()
        print "\nError: Neither run or stop are specified"
        return -1

    if options.freq < 0:
        parser.print_help()
        print "\nError: Invalid frequency specified"
        return -1

    if not 0<=options.duty <=100:
        parser.print_help()
        print "\nError: Invalid duty specified\nexpected: 0<=duty <=100"
        return -1

    pwm=PWM(options.freq)

    if options.run:
        pwm.set_duty(options.duty)
        pwm.run()
    else:
        pwm.stop()

if __name__ ==  '__main__':
    sys.exit(main())

