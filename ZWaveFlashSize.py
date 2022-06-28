''' Z-Wave FLASH size calculator

    This Python program searches thru a GCC .MAP file and sums the flash used 
    in each of several categories.
    This program relies on string matching in the .MAP file to categorize the flash used.
    Different strings are needed for other types of projects. 
    Customization for other projects has been enabled by using variables to define the different categories.

    The syntax and format of the .map file is assumed to match the format from the 10.xx release of GCC.
    Any changes to the format would require some recoding but as you can see this program is pretty simple so it shouldn't be hard.

    The accuracy of the size calculations and the categorization depends on many factors mostly around the format of the .map file.
    Do NOT expect the size calculations to be accurate down to the byte. Expect maybe 1/2K byte accuracy.
    Accuracy all depends on how well the very simple strings in categories match the map file.
    Feel free to customize the category strings to improve their accuracy. 
    Set DEBUG=9 to see how the categories are matching the map file.

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
import string

VERSION       = "0.8 - 6/28/2022"       # Version of this python program
DEBUG         = 3     # [0-10] higher values print out more debugging info - 0=off

'''
  The first line has the total FLASH used it seems - is this without the .fill though? Doesn't quite match the end of the hex file.
  Many lines are broken across 2 so first thing to do is join them together
  stop when the address is outside of flash (or ORIGIN (RAM))
'''

''' Categories is a dictionary of the strings used to categorize each line of the map file
    The ORDER of the categories is important as the first matching category is the one used.
    Thus, in the case where 2 or more categories might match the same line, the first one is selected.
    This section can be customized for any type of project - this one is specific to Z-Wave for GSDK 4.1.
'''
categories = {
 "GCC"          : "/lib/gcc/",      # GCC Libraries
 "BOOTLOADER"   : "platform/bootloader",# bootloader INTERFACE code (does NOT include the bootloader itself)
 "RAIL"         : "/rail_lib/",     # Radio Interface
 "NVM3CODE"     : "nvm3",           # NVM3
 "CRYPTO"       : "/crypto/",       # Encryption libraries
 "FREERTOS"     : "/freertos/",     # FreeRTOS 
 "ZAF"          : "/ZAF",    # Z-Wave Application Framework
 "ZWAVE"        : "/z-wave/",       # Z-Wave protocol
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
        if DEBUG>6: print("DiscardedSize={}".format(DiscardedSize))
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
            
    def isHex(astring):
        try:
            int(astring,16)
            return True
        except ValueError:
            return False

    def CalculateMap(self):
        ''' scan thru the map file and calculate and return the size of each category'''
        size = {"FILL" : 0} # start with the fill category which is special
        for cat in categories.keys():   # instantiate the dict
            size[cat]=0
        line=[]
        while True:                     # read each line of the .MAP file and add the size to the respective category
            if len(line)<3:             # ignore lines with less than 3
                if DEBUG>9: print(" - Ignored {}".format(line))
            elif not ZWaveFlashSize.isHex(line[1]):    # ignore lines that don't have a hex address
                if DEBUG>8: print(" - Not Hex {}".format(line))
            elif len(line)==4:
                found=False
                for cat in categories.keys():
                    if categories[cat] in line[3]:
                        found=True
                        size[cat] += int(line[2],16)
                        if DEBUG>5: print("Category={} size={} added {} line= {}".format(cat,size[cat],int(line[2],16),line))  # Set DEBUG above this value to check the categorization
                        break
                if not found and DEBUG>8: print(" - No category for line={}".format(line))
            elif len(line)==3:  # the fill lines don't have a file name field
                if "*fill*" in line[0]:
                    size["FILL"] += int(line[2],16)
                elif int(line[1],16)>=0x20000000: # if in RAM section then exit
                    break
                elif DEBUG>8: print(" - Skipped line={}".format(line))
            elif len(line)>=1:          # end of the .text section starts with the .stack in RAM
                if ".stack" in line[0]:
                    if DEBUG>8: print("End {}".format(line))
                    break
            else:
                if DEBUG>8: print(" - Dropped line {}".format(line))
            line = self.getFields() # get the next line
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
    except Exception as err:
        print("Error {}".format(err.args))
        ZWaveFlashSize.usage()
        exit()

    DiscardedSize = self.CalculateDiscarded()   # Calculate the discarded code size which is usually huge since it has a ton of debugging info in it
    TextSize = self.findTextSize()              # find the .text total size line
    size = self.CalculateMap()                  # categorize each line of the .map file and sum up the size in each
    total=0
    for cat in size.keys():                     # print out the results
        print("Category {:11s} Size={:>6.1f}KB".format(cat,round(size[cat]/1024,1)))
        total += size[cat]
    print("Categories Total={}KB {}% of 800 series FLASH (240K max)".format(round(total/1024,1),round(total*100/(240*1024),1)))
    if DEBUG>4: print("TextSize={} {}KB".format(TextSize,round(TextSize/1024,1)))
    if DEBUG>5: print("DiscardedSize={} {}KB".format(DiscardedSize,round(DiscardedSize/1024,1)))

    exit()
