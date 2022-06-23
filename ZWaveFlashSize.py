''' Z-Wave FLASH size calculator

    This Python program searches thru a GCC .MAP file and sums the flash used 
    in each of several categories.
    This program relies on string matching in the .MAP file to categorize the flash used.

    This program is a DEMO only and is provided AS-IS and without support. 
    But feel free to copy and improve!

    Usage: python ZWaveFlashSize.py <filename>.axf

   Testing:
    This program was tested in Windows and may require some tweaks for other platforms.

   Resources:
   https://community.silabs.com/s/article/interpreting-the-gcc-map-file-in-simplicity-ide
   https://interrupt.memfault.com/blog/get-the-most-out-of-the-linker-map-file

'''

import sys
import time
import os

VERSION       = "0.1 - 6/22/2022"       # Version of this python program
DEBUG         = 10     # [0-10] higher values print out more debugging info - 0=off

'''
  Categories - not sure how to handle this yet but ideally there's a few strings defined here that in turn filter the data into the appropriate category.
  DISCARDED - Should I add up all the discarded code? yes! - that comes from the discarded section of the file and the addr is always 0. Filter these down to add up just whats been removed from each obj file. Ends at Memory Configuration
  FILL  - "*fill* - these are the small blocks used to align the next chunk of code
  GCC   - "lib/gcc" - libraries out of the GCC compiler this is in the long string of the code
  GECKO - "gecko_sdk_" - hardware drivers and other platform code (but only after the ones below are already processed) - maybe filter on something else???
  BOOTLOADER    - "platform/bootloader" - subtract these from GECKO
  RAIL  - "rail_lib" - subtract from GECKO
  ZAF   - "z-wave/ZAF" - subtract from GECKO
  ZWAVE - "z-wave/platform" || "z-wave/ZWave/lib"- subtract from GECKO
  CRYPTO - "/crypto/" - subtract from GECKO
  FREERTOS - "/freertos/" - same
  NVM3CODE - "/nvm3/lib/libnvm3" - same


  The first line has the total FLASH used it seems - is this without the .fill though? Doesn't quite match the end of the hex file.
  Many lines are broken across 2 so first thing to do is join them together
  Only look at lines that have .text in them. skip any line missing the size. or .rodata or _cc_handlers? 
  stop when the address is outside of flash (or ORIGIN (RAM))


'''
class ZWaveFlashSize():
    ''' Z-Wave Flash Size Calculator '''
    def __init__(self):         
        ''' open the .map file and instance some structures '''
        if len(sys.argv)==1:    # no arguments
            raise ValueError("No Map file given")
        try:
            self.mapfile = open(sys.argv[1],"r")
            if DEBUG>7:print("Opened {}".format(sys.argv[1]))
        except:
            raise ValueError("Unable to open",sys.argv[1])


    def getFields(self):
        ''' Return the next line of the map file which has 4 fields - Type, address, size, filename
            The line of text is often broken across 2 lines in the file if the Type is too long'''
        s2 = ""
        s1 = self.mapfile.readline()
        if not s1:       # if EOF
            raise ValueError("EOF found prematurely")
        if len(s1.split()) == 1: # if the line only has the symbol on it, concatenate the next line which has the rest of the fields
            s2 = self.mapfile.readline()
        s3 = s1 + s2
        return(s3.split())


    def findDiscarded(self):
        ''' scan thru the .map file to find the discarded section'''
        i=0;
        s = ""
        while "Discarded input sections" not in s:
            s = self.mapfile.readline()
            if not s:       # if EOF
                raise ValueError("MAP file format error - didn't find Discarded input section")
            i+=1
        if DEBUG>8: print("Skipped {} lines to the Discarded section".format(i))

    def CalculateDiscarded(self):
        ''' Sum the discarded code section'''
        DiscardedSize=0
        self.findDiscarded()
        largestSize=0
        line = []
        while True:
            if len(line)>=2 and "Memory" in line[0] and "Configuration" in line[1]: # end of discarded section
                break
            elif len(line)==1: # only 1 word which is usually the symbol
                line = self.getFields()
            elif len(line)!=4: # skip lines that have the wrong number of fields
                pass
            else:
                try:
                    size = int(line[2],16)
                    DiscardedSize += size
                    if largestSize<size:
                        largestSize=size
                        if DEBUG>8: print("largest Discard so far={} {}".format(size, line[3]))
                except: # skip the line if size isn't hex
                    if DEBUG>5: print("size is not hex {}".format(line))
            line = self.getFields() # get the next line
        if DEBUG>3: print("DiscardedSize={}".format(DiscardedSize))
        return(DiscardedSize)
                

    def usage():
        print("")
        print("Usage: python ZWaveFlashSize.py <filename>.map")
        print("Version {}".format(VERSION))
        print("")

if __name__ == "__main__":
    ''' Start the app if this file is executed'''

    try:
        self=ZWaveFlashSize()       # open the .MAP file
        DiscardedSize = self.CalculateDiscarded()   # Calculate the discarded code size which is usually huge since it has a ton of debugging info in it

    except Exception as err:
        print("Error {}".format(err.args))
        ZWaveFlashSize.usage()
        exit()


    exit()
