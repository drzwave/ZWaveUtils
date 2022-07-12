''' Z-Wave FLASH/RAM size calculator

    This Python program searches thru a GCC .MAP file and sums the flash used 
    in each of several categories.
    This program relies on string matching in the .MAP file to categorize the flash used.
    Different strings are needed for other types of projects. 
    Customization for other projects has been enabled by using variables to define the different categories.

    The syntax and format of the .map file is assumed to match the format from the 10.xx release of GCC.
    Any changes to the format would require some recoding but as you can see this program is pretty simple so it shouldn't be hard.

    The accuracy of the size calculations and the categorization depends on many factors mostly around the format of the .map file.
    Do NOT expect the size calculations to be accurate down to the byte. Expect maybe +/- 100 byte accuracy.
    Accuracy all depends on how well the very simple strings in categories match the map file.
    Feel free to customize the category strings to improve their accuracy. 
    Set DEBUG=9 to see how the categories are matching the map file. Look for UNKNOWN category which means nothing is matching.

    This program is a DEMO only and is provided AS-IS and without support. 
    But feel free to copy and improve!

    Usage: python ZWaveFlashSize.py <filename>.axf

   Testing:
    This program was tested in Windows and may require some tweaks for other platforms and uses Python3.

   Resources:
   https://community.silabs.com/s/article/interpreting-the-gcc-map-file-in-simplicity-ide
   https://interrupt.memfault.com/blog/get-the-most-out-of-the-linker-map-file

'''

import sys
import time
import os
import string

VERSION       = "0.9 - 7/12/2022"       # Version of this python program
DEBUG         = 1     # [0-10] higher values print out more debugging info - 0=off

'''
  Many lines are broken across 2 so first thing to do is join them together
  stop when the address is outside of flash (or ORIGIN (RAM))
'''

#################Customize these Dictionaries to match your .MAP file ################################
''' FlashCategories is a dictionary of the strings used to categorize each line of the map file
    The ORDER of the categories is important as the first matching category is the one used.
    Thus, in the case where 2 or more categories might match the same line, the first one is selected.
    This section can be customized for any type of project - this one is specific to Z-Wave for GSDK 4.1.
'''
FlashCategories = {
 "GCC"          : "/lib/gcc/",      # GCC Libraries
 "BOOTLOADER"   : "platform/bootloader",# bootloader INTERFACE code (does NOT include the bootloader itself)
 "RAIL"         : "/rail_lib/",     # Radio Interface
 "NVM3CODE"     : "nvm3",           # NVM3
 "CRYPTO"       : "/crypto/",       # Encryption libraries
 "FREERTOS"     : "/freertos/",     # FreeRTOS 
 "ZAF"          : "/ZAF",           # Z-Wave Application Framework
 "ZWAVE"        : "/z-wave/",       # Z-Wave protocol
 "GECKO"        : "gecko_sdk_",     # Gecko platform code - peripheral drivers etc
 "APPLICATION"  : "/"               # everything left over is assumed to be the application
}

''' RAMCategories is the same concept as above but for RAM '''
RAMCategories = {
 "Stack"        : "QQstack",        # CPU Stack is a special category which has to match the NAME field instead of the file field
 "Heap"         : "QQheap",         # CPU heap
 "BOOTLOADER"   : "platform/bootloader",# bootloader INTERFACE code (does NOT include the bootloader itself)
 "RAIL"         : "/rail_lib/",     # Radio Interface
 "CRYPTO"       : "/crypto/",       # Encryption libraries
 "FREERTOS"     : "/freertos/",     # FreeRTOS 
 "ZAF"          : "/ZAF",           # Z-Wave Application Framework
 "ZWAVE"        : "/z-wave/",       # Z-Wave protocol
 "Platform"     : "/platform",      # Platform code (clocks, power mgr, drivers, etc)
 "APPLICATION"  : "/"               # everything left over is assumed to be the application
}
###################################################################################################

class ZWaveFlashSize():
    ''' Z-Wave Flash/RAM Size Calculator '''
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
        ''' Return the next line of the map file which has 4 fields - Type.symbol, address, size, filename
            The line of text is often broken across 2 lines in the file if the Type is too long.
            Skip lines that don't match the necessary format.
        '''
        s2 = ""
        while (True):
            s1 = self.mapfile.readline()
            if not s1:       # if EOF
                raise ValueError("EOF found prematurely")
            if (len(s1.split()) == 3 or len(s1.split()) == 4) and ZWaveFlashSize.isHex(s1.split()[1]) and ZWaveFlashSize.isHex(s1.split()[2]):
                # if 3 or 4 fields found and addr/len is hex, then return them, otherwise more processing required
                break
            elif len(s1.split()) == 1: # if the line only has the type.symbol on it, concatenate the next line which often has the rest of the fields
                    s2 = s1             # save the type.symbol
            elif len(s1.split()) == 3:
                if ZWaveFlashSize.isHex(s1.split()[0]): # most common is the Type is on one line followed by the other 3 fields on the next line
                    s1 = s2 + s1
                    break           # found all 4 fields and the address is hex so looks like a good line - return them
                else:
                    if DEBUG>9: print("  -discarded {}".format(s1))
            else:
                if DEBUG>9: print("  -Discarded {}".format(s1))
        return(s1.split())


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
            line = self.getFields() # get the next line
            if len(line)>=2 and "FLASH" in line[0]: # end of discarded section (Memory Configuration section lists the size of FLASH and RAM)
                break
            elif len(line)>=2:
                size = int(line[2],16)
                DiscardedSize += size
                if largestSize<size:
                    largestSize=size
                    if DEBUG>8: print("largest Discard so far={} {}".format(size, line[3]))
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

    def CalculateFLASH(self):
        ''' scan thru the map file and calculate and return the size of each category
            Start with the .text line and end with the .stack line
        '''
        if DEBUG>5: print("Begin FLASH")
        size = {"FILL" : 0} # start with the fill category which is special
        for cat in FlashCategories.keys():   # instantiate the dict
            size[cat]=0
        line=[]
        while True:                     # read each line of the .MAP file and add the size to the respective category
            if len(line)<3:             # ignore lines with less than 3
                if DEBUG>9: print(" - Ignored {}".format(line))
            elif not ZWaveFlashSize.isHex(line[1]):    # ignore lines that don't have a hex address
                if DEBUG>8: print(" - Not Hex {}".format(line))
            elif len(line)==4:
                found=False
                for cat in FlashCategories.keys():
                    if FlashCategories[cat] in line[3]:
                        found=True
                        size[cat] += int(line[2],16)
                        if DEBUG>5: print("Category={} size={} added {} line= {}".format(cat,size[cat],int(line[2],16),line))  # Set DEBUG above this value to check the categorization
                        break
                if not found and DEBUG>8: print(" -UNKNOWN No category for line={}".format(line))
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
            

    def CalculateRAM(self):
        ''' scan thru the map file and calculate and return the size of each category.
            Start with the .stack line and end with the .heap line.
            Assume the MAP file is already pointing at the STACK line when called.
        '''
        if DEBUG>5: print("Begin RAM")
        size = {"FILL" : 0} # start with the fill category which is special
        for cat in RAMCategories.keys():   # instantiate the dict
            size[cat]=0
        line=[]
        done=False
        while not done:                     # read each line of the .MAP file and add the size to the respective category
            line = self.getFields()     # get the next line
            if len(line)<3:             # ignore lines with less than 3
                if DEBUG>9: print(" - Ignored {}".format(line))
            elif len(line)==4:
                found=False
                for cat in RAMCategories.keys():
                    if ".stack" in line[0]:
                        found=True
                        size["Stack"] += int(line[2],16)
                        if DEBUG>5: print("Stack={}".format(size["Stack"]))
                        break
                    if ".heap" in line[0]:
                        found=True
                        done=True
                        size["Heap"] += int(line[2],16)
                        break
                    elif RAMCategories[cat] in line[3]:
                        found=True
                        size[cat] += int(line[2],16)
                        if DEBUG>5: print("RAM Category={} size={} added {} line= {}".format(cat,size[cat],int(line[2],16),line))  # Set DEBUG above this value to check the categorization
                        break
                if not found and DEBUG>8: print(" -UNKNOWN No category for line={}".format(line))
            elif len(line)==3:  # the fill lines don't have a file name field
                if "*fill*" in line[0]:
                    size["FILL"] += int(line[2],16)
                elif DEBUG>8: print(" - Skipped line={}".format(line))
            else:
                if DEBUG>8: print(" - Dropped line {}".format(line))
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
    flash   = self.CalculateFLASH()             # categorize each line of the FLASH section of the .map file and sum up the size in each
    ram     = self.CalculateRAM()               # categorize each line of the RAM section of the .map file and sum up the size in each
    total=0
    print("FLASH:")
    for cat in flash.keys():                     # print out the results
        print("Category {:11s} Size={:>6.1f}KB".format(cat,round(flash[cat]/1024,1)))
        total += flash[cat]
    print("FLASH Total={}KB {}% of 800 series FLASH (240K max)".format(round(total/1024,1),round(total*100/(240*1024),1)))
    print("RAM:")
    ramtotal=0
    for cat in ram.keys():                     # print out the results
        print("Category {:11s} Size={:>6.1f}KB".format(cat,round(ram[cat]/1024,1)))
        ramtotal += ram[cat]
    print("RAM Total={}KB {}% of RAM (64K max)".format(round(ramtotal/1024,1),round(ramtotal*100/(64*1024),1)))
    if DEBUG>4: print("TextSize={} {}KB".format(TextSize,round(TextSize/1024,1)))
    if DEBUG>5: print("DiscardedSize={} {}KB".format(DiscardedSize,round(DiscardedSize/1024,1)))

    exit()
