''' Z-Wave FLASH size calculator

    This Python program searches thru a GCC .MAP file and sums the flash used 
    in each of several categories.
    This program relies on string matching in the .MAP file to categorize the flash used.
    Different strings are needed for other types of projects. 
    Customization for other projects has been enabled by using variables to define the different categories.

    The syntax and format of the .map file is assumed to match the format from the 10.xx release of GCC.
    Any changes to the format would require some recoding but as you can see this program is pretty simple so it shouldn't be hard.

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

VERSION       = "0.2 - 6/24/2022"       # Version of this python program
DEBUG         = 10     # [0-10] higher values print out more debugging info - 0=off

'''
  The first line has the total FLASH used it seems - is this without the .fill though? Doesn't quite match the end of the hex file.
  Many lines are broken across 2 so first thing to do is join them together
  stop when the address is outside of flash (or ORIGIN (RAM))
'''

''' Categories is a dictionary of the strings used to categorize each line of the map file
    The order of the categories is important as the first matching category is the one used.
    Thus, in the case where 2 or more categories might match the same line, the first one is the one used.
'''
categories = {
 "GCC"          : "/lib/gcc/",      # GCC Libraries
 "BOOTLOADER"   : "platform/bootloader",    # bootloader code which includes SE interface
 "RAIL"         : "/rail_lib/",     # Radio Interface
 "ZAF"          : "/z-wave/ZAF",    # Z-Wave Application Framework
 "ZWAVE"        : "/z-wave/",       # Z-Wave protocol
 "CRYPTO"       : "/crypto/",       # Encryption libraries
 "FREERTOS"     : "/freertos/",     # FreeRTOS 
 "NVM3CODE"     : "/nvm3/lib/libnvm3",# NVM3
 "GECKO"        : "gecko_sdk_",     # Gecko platform code - peripheral drivers etc
 "APPLICATION"  : "/"               # everything left over is assumed to be the application
}

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
            elif len(line)==1: # only 1 word which is usually the symbol    - TODO is this needed??? getfields handles this on its own
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
                
    def findTextSize(self):
        ''' scan thru the .map file to find the first .text line in the memory map and return the total .text size'''
        line = []
        while True:
            if len(line)!=3:
                line = self.getFields()
            elif ".text" not in line[0]:
                line = self.getFields()
            else:
                break
        return(int(line[2],16))
            
    def CalculateMap(self):
        ''' scan thru the map file and calculate and return the size of each category'''
        size = {"FILL" : 0} # start with the fill category which is special
        for cat in categories.keys():
            size[cat]=0
        line=[]
        while True:
            if len(line)==4:
                for cat in categories.keys():
                    if categories[cat] in line[3]:
                        size[cat] += int(line[2],16)
                        if DEBUG>5: print("categorty={} size={} added {} line= {}".format(cat,size[cat],int(line[2],16),line))
                        break
            elif len(line)==3:
                if "*fill*" in line[0]:
                    size["FILL"] += int(line[2],16)
            elif len(line)>=1:          # end of the .text section starts with the .stack in RAM
                if ".stack" in line[1]:
                    break
            line = self.getFields()
        for cat in size.keys():
            print("Category {} Size={}".format(cat,size[cat]))
        return(size)
            

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
        textsize = self.findTextSize()              # find the .text total size line
        print("textsize={}".format(textsize))
        self.CalculateMap()

    except Exception as err:
        print("Error {}".format(err.args))
        ZWaveFlashSize.usage()
        exit()


    exit()
