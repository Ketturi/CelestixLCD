# -*- coding: utf-8 -*-
"""
Copyright (C) 2020 Henri "Ketturi" Keinonen

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whomthe Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import hid
import subprocess

class CelestixLCD(object):
    """
    Provides methods to get key events from Celestix knob
    and update text and symbols to LCD device
    """
    kbd_report = b'\x01' # HID Report number of input knob
    lcd_report = b'\x02' # HID Report number of alphanumeric LCD
    
    cmd_text  = b'\x00' # LCD command to write LCD text buffer
    cmd_clear = b'\x01' # LCD command to clear/init LCD
    cmd_char  = b'\x03' # LCD command to write character memory
    
    cmd_clear_len = 6
    
    def __init__(self):
        # Find matching USB HID devic
        self._vid = 0x0CB6
        self._pid = 0x0002
        devices = hid.enumerate(self._vid,self._pid)
        if not devices:
            raise RuntimeError('Cannot find USB LCD device')
        self._path = devices[0]['path']

        # Open hid device
        self._device = hid.Device(path=self._path)
        #assert self._device is isinstance(hid.Device)
    
    def __enter__(self):
        return self
    
    def __del__(self):
        self.close
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()
        
    def read(self, timeout=None, beep=False):
        """
        Read from the keyboard (rotary encoder)
        device that is attached to the LCD display.

        :param timeout: If given, read timeouts after given ms
        :type timeout: int

        :param beep: If set, beeps from system speaker with every
            user interaction.
        :type beep: boolean

        """
        keycode = self._device.read(6, timeout)
        if keycode == b'\x01\x02\x3A': #0x02 0x3A Shift+F1
            if beep: subprocess.call(["/usr/bin/beep", "-f 1000" , "-l 20"])
            return 'select'
        elif keycode == b'\x01\x02\x3B': #0x02 0x3B Shift+F2
            if beep: subprocess.call(["/usr/bin/beep", "-f 500" , "-l 10"])
            return 'right'
        elif keycode == b'\x01\x02\x3C': #0x02 0x3C Shift+F3
            if beep: subprocess.call(["/usr/bin/beep", "-f 500" , "-l 10"])
            return 'left'
        else:
            print(keycode)
            
    def readRaw(self, timeout=None):
        """ Read raw data from open usb hid device """
        return self._device.read(63, timeout).hex()
        
    def writeRaw(self, data):
        """ Write raw data packet to usb hid device """
        self._device.write(data)
    
    def clear(self):
        """ Clears LCD text memory """
        command = self.lcd_report + self.cmd_clear + bytes(6)
        self._device.write(command)
     
    def write_line(self, string, line=0):
        """
        Writes one line of text to LCD,
        fills rest with blank spaces.

        :param string: Can be text and special characters.
        :type string: default python utf-8 string

        :param line: Selects top or bottom line where string is written.
        :type line: int
        
        """
        message = string[:40] # Force string to fit into the display line
        assert 0 <= line <=1,'Line must be 0 or 1.'
        
        cursor_pos = 0 # Write from begining of the line
        length = 40 # LCD length
        endpad = b' ' * (40 - len(message)) # Fill buffer with spaces

        #USB HID packet
        payload = (self.lcd_report + 
                   self.cmd_text + 
                   cursor_pos.to_bytes(1,'big') + 
                   line.to_bytes(1,'big') + 
                   length.to_bytes(1,'big') + 
                   bytes(3) + 
                   message.encode('iso-8859-1','replace') + 
                   endpad)
        self._device.write(payload)
    
    def write_string(self, string, line=0, cursor=0):
        """
        Writes string to specified line and position
        
        :param string: Can be text and special characters.
        :type string: default python utf-8 string

        :param line: Selects top or bottom line where string is written.
        :type line: int

        :param cursor: Selects cursor positon 0-39, where string is written.
        :type cursor: int
        
        """ 
        message = string[:40] #Force string to fit into the display
        assert 0 <= line <=1,'Line must be 0 or 1'
        assert 0 <= cursor <=39, 'Cursor must be 0-39'      
        length = len(message)

        #USB HID packet
        payload = (self.lcd_report + 
                   self.cmd_text + 
                   cursor.to_bytes(1, 'big') + 
                   line.to_bytes(1, 'big') + 
                   length.to_bytes(1, 'big') + 
                   bytes(3) + 
                   message.encode('iso-8859-1','replace'))
        self._device.write(payload)
        
    def create_char(self, location, bitmap):
        """Write custom characters to LCD memory

        LCD supports up to 6 custom characters,
        7-8 are internal and can't be changed.
        
        :param location: The place in display memory where the
            characters are written.
            Value needs to be integer from 0 to 7.
        :type location: int

        :param bitmap: Bitmap containing character data.
            This should be tuple of 1 to 48 numbers, each
            represents 5 pixel in a row.
        :type bitmap: tuple of int

        """
        assert 0 <= location <=7, 'Only locations 0-7 can be used'
        assert 1 <= len(bitmap) <=48, 'Bitmap should have 1-48 rows'
        
        startpos = location*8
        charData = b''

        #Loop trough bitmap and add into data packet
        for row in bitmap:
            charData = charData + row.to_bytes(1, 'big')
        length = len(charData)

        #USB HID packet
        payload = (self.lcd_report + 
                   self.cmd_char + 
                   startpos.to_bytes(1,'big') + 
                   b'\x00' + 
                   length.to_bytes(1,'big') + 
                   bytes(3) + 
                   charData)
        self._device.write(payload)
        
    def close(self):
        """Closed connection to USB HID device """
        if self._device:
            self._device.close()
