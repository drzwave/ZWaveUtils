''' Z-Wave 500 series NVM utilities

    This Python program can be used to extract the Z-Wave network and routing
    information from a 500 series SerialAPI.
    The SerialAPI verision must be at least 6.51.02 or later as previous versions
    do not have the extended NVM functions needed. The only way to extract the NVM 
    from older units is via a Z-Wave programmer like the ZDP03A and the PC Programmer tool.
    The NVM cannot be extracted from the SerialAPI in these older units.
    If you have an older unit, the recommendation is to rebuild the Z-Wave network by 
    excluding the devices and including them into the new controller.

    This program is a DEMO only and is provided AS-IS and without support. 
    But feel free to copy and improve!

    Usage: python ZWaveNVM500.py [COMx]
    COMx is optional and is the COM port or /dev/tty* port of the Z-Wave interface.

   Resources:
   INS13954 - Z-Wave 500 Application Programmers Guide - https://www.silabs.com/documents/login/user-guides/INS13954-Instruction-Z-Wave-500-Series-Appl-Programmers-Guide-v6_81_0x.pdf
'''

import serial           # serial port control
from intelhex import IntelHex   # utilities for reading in the hex file - "pip install intelhex" if you don't already have it
import sys
import time
import os
from struct            import * # PACK


#COMPORT       = "/dev/ttyAMA0" # Serial port default - typically /dev/ttyACM0 on Linux
COMPORT       = "COM14" # Serial port default - On Windows it will be via a COMxx port

VERSION       = "0.5 - 11/24/2020"       # Version of this python program
DEBUG         = 4     # [0-10] higher values print out more debugging info - 0=off

# Handy defines mostly copied from ZW_transport_api.py
FUNC_ID_SERIAL_API_GET_INIT_DATA    = b'\x02'
FUNC_ID_SERIAL_API_APPL_NODE_INFORMATION = b'\x03'
FUNC_ID_SERIAL_API_GET_CAPABILITIES = b'\x07'
FUNC_ID_SERIAL_API_SOFT_RESET       = b'\x08'
FUNC_ID_ZW_GET_PROTOCOL_VERSION     = b'\x09'
FUNC_ID_SERIAL_API_STARTED          = b'\x0A'
FUNC_ID_ZW_SET_RF_RECEIVE_MODE      = b'\x10'
FUNC_ID_ZW_SEND_DATA                = b'\x13'
FUNC_ID_ZW_GET_VERSION              = b'\x15'
FUNC_ID_NVM_EXT_READ_LONG_BUFFER    = b'\x2A'
FUNC_ID_NVM_EXT_WRITE_LONG_BUFFER   = b'\x2B'
FUNC_ID_NVM_EXT_READ_LONG_BYTE      = b'\x2C'
FUNC_ID_NVM_EXT_WRITE_LONG_BYTE     = b'\x2D'
FUNC_ID_ZW_ADD_NODE_TO_NETWORK      = b'\x4A'
FUNC_ID_ZW_REMOVE_NODE_FROM_NETWORK = b'\x4B'
FUNC_ID_ZW_FIRMWARE_UPDATE_NVM      = b'\x78'

# Firmware Update NVM commands
FIRMWARE_UPDATE_NVM_INIT            = b'\x00'
FIRMWARE_UPDATE_NVM_SET_NEW_IMAGE   = b'\x01'
FIRMWARE_UPDATE_NVM_GET_NEW_IMAGE   = b'\x02'
FIRMWARE_UPDATE_NVM_UPDATE_CRC16    = b'\x03'
FIRMWARE_UPDATE_NVM_IS_VALID_CRC16  = b'\x04'
FIRMWARE_UPDATE_NVM_WRITE           = b'\x05'

# Z-Wave Library Types
ZW_LIB_CONTROLLER_STATIC  = 0x01
ZW_LIB_CONTROLLER         = 0x02
ZW_LIB_SLAVE_ENHANCED     = 0x03
ZW_LIB_SLAVE              = 0x04
ZW_LIB_INSTALLER          = 0x05
ZW_LIB_SLAVE_ROUTING      = 0x06
ZW_LIB_CONTROLLER_BRIDGE  = 0x07
ZW_LIB_DUT                = 0x08
ZW_LIB_ZERONINE           = 0x09
ZW_LIB_AVREMOTE           = 0x0A
ZW_LIB_AVDEVICE           = 0x0B
libType = {
ZW_LIB_CONTROLLER_STATIC  : "Static Controller",
ZW_LIB_CONTROLLER         : "Controller",
ZW_LIB_SLAVE_ENHANCED     : "Slave Enhanced",
ZW_LIB_SLAVE              : "Slave",
ZW_LIB_INSTALLER          : "Installer",
ZW_LIB_SLAVE_ROUTING      : "Slave Routing",
ZW_LIB_CONTROLLER_BRIDGE  : "Bridge Controller",
ZW_LIB_DUT                : "DUT",
ZW_LIB_ZERONINE           : "UNKNOWN",
ZW_LIB_AVREMOTE           : "AVREMOTE",
ZW_LIB_AVDEVICE           : "AVDEVICE" }

ADD_NODE_ANY       =         b'\x01'
ADD_NODE_CONTROLLER=         b'\x02'
ADD_NODE_SLAVE     =         b'\x03'
ADD_NODE_EXISTING  =         b'\x04'
ADD_NODE_STOP      =         b'\x05'
ADD_NODE_SMART_START =       b'\x09'
TRANSMIT_COMPLETE_OK      =  b'\x00'
TRANSMIT_COMPLETE_NO_ACK  =  b'\x01'
TRANSMIT_COMPLETE_FAIL    =  b'\x02'
TRANSMIT_ROUTING_NOT_IDLE =  b'\x03'
TRANSMIT_OPTION_ACK =        b'\x01'
TRANSMIT_OPTION_AUTO_ROUTE = b'\x04'
TRANSMIT_OPTION_EXPLORE =    b'\x20'
# SerialAPI defines
SOF = b'\x01'
ACK = b'\x06'
NAK = b'\x15'
CAN = b'\x18'
REQUEST  = b'\x00'
RESPONSE = b'\x01'
# Most Z-Wave commands want the autoroute option on to be sure it gets thru. Don't use Explorer though as that causes unnecessary delays.
TXOPTS = bytes([TRANSMIT_OPTION_AUTO_ROUTE[0] | TRANSMIT_OPTION_ACK[0]])

# See INS13954-12 section 7 Application Note: Z-Wave Protocol Versions on page 433
ZWAVE_VER_DECODE = {# Z-Wave version to SDK decoder: https://www.silabs.com/products/development-tools/software/z-wave/embedded-sdk/previous-versions
        b"6.09" : "SDK 6.82.01 04/2020",
        b"6.08" : "SDK 6.82.00 Beta   ",
        b"6.07" : "SDK 6.81.06 07/2019",
        b"6.06" : "SDK 6.81.05        ",
        b"6.05" : "SDK 6.81.04        ",
        b"6.04" : "SDK 6.81.03 01/2019",
        b"6.03" : "SDK 6.81.02        ",
        b"6.02" : "SDK 6.81.01 10/2018",
        b"6.01" : "SDK 6.81.00 09/2018",
        b"5.03" : "SDK 6.71.03        ",
        b"5.02" : "SDK 6.71.02 07/2017",
        b"4.61" : "SDK 6.71.01 03/2017",
        b"4.60" : "SDK 6.71.00 01/2017",
        b"4.62" : "SDK 6.61.01 04/2017",  # This is the INTERMEDIATE version?
        b"4.33" : "SDK 6.61.00 04/2016",
        b"4.54" : "SDK 6.51.10 02/2017",
        b"4.38" : "SDK 6.51.09 07/2016",
        b"4.34" : "SDK 6.51.08 05/2016",
        b"4.24" : "SDK 6.51.07 02/2016",
        b"4.05" : "SDK 6.51.06 06/2015 or SDK 6.51.05 12/2014",
        b"4.01" : "SDK 6.51.04 05/2014",
        b"3.99" : "SDK 6.51.03 07/2014",
        b"3.95" : "SDK 6.51.02 05/2014",
        b"3.92" : "SDK 6.51.01 04/2014",
        b"3.83" : "SDK 6.51.00 12/2013",
        b"3.79" : "SDK 6.50.01        ",
        b"3.71" : "SDK 6.50.00        ",
        b"3.35" : "SDK 6.10.00        ",
        b"3.41" : "SDK 6.02.00        ",
        b"3.37" : "SDK 6.01.03        "
        }

class ZWaveNVM500():
    ''' Z-Wave 500 series NVM extractor '''
    def __init__(self):         # parse the command line arguments and open the serial port
        self.COMPORT=COMPORT
        self.filename="NVM.hex"
        if len(sys.argv)==1:     # No arguments then just print the status if the default serial port can be opened
            pass
        elif "COM" in sys.argv[1] or "tty" in sys.argv[1]: # SerialAPI port
            self.COMPORT=sys.argv[1]
        else:
            self.usage()
            sys.exit()
        if DEBUG>3: print("COM Port set to {}".format(self.COMPORT))
        try:
            self.UZB= serial.Serial(port=self.COMPORT,baudrate=115200,timeout=2)
        except serial.SerialException:
            print("Unable to open serial port {}".format(self.COMPORT))
            raise
        self.NVM=IntelHex() # create the NVM instance

    def checksum(self,pkt):
        ''' compute the Z-Wave SerialAPI checksum at the end of each frame'''
        s=0xff
        for c in pkt:
            s ^= c
        return bytes([s])

    def GetRxChar( self, timeout=100):
        ''' Get a character from the UART or timeout in 100ms'''
        while timeout >0 and not self.UZB.in_waiting:
            time.sleep(0.001)
            timeout -=1
        if timeout>0:
            retval= self.UZB.read()
        else:
            retval= None
            print("got nothing")
        if DEBUG>9: print(" {:02X}".format(ord(retval)), end='') # this is handy to see all the bytes being received
        return retval

    def GetZWave( self, timeout=5000):
        ''' Receive a frame from the UART and return bytearray or timeout in TIMEOUT ms and return None'''
        pkt=b''
        c=self.GetRxChar(timeout)
        if c == None:
            if DEBUG>1: print("GetZWave Timeout!")
            return None
        while c!=SOF:   # get synced on the SOF
            if DEBUG>5: print("SerialAPI Not SYNCed {:02X}".format(ord(c)))
            c=self.GetRxChar(timeout)
        if c!=SOF:
            return None
        length=self.GetRxChar()[0]
        for i in range(length):
            c=self.GetRxChar()
            pkt += c
        checksum= self.checksum(pkt)[0]
        checksum ^= length  # checksum includes the length
        if checksum!=0:
            if DEBUG>1: print("GetZWave checksum failed {:02x}".format(checksum))
        self.UZB.write(ACK)  # ACK the returned frame - we don't send anything else even if the checksum is wrong
        return pkt[1:-1] # strip off the type and checksum
 
 
    def Send2ZWave( self, SerialAPIcmd, returnStringFlag=False, timeout=5000):
        ''' Send the command via the SerialAPI to the Z-Wave chip and optionally wait for a response.
            If ReturnStringFlag=True then returns bytes of the SerialAPI frame response within TIMEOUT ms
            else returns None
            Waits 100ms for the ACK/NAK/CAN for the SerialAPI and strips that off. 
            Removes all SerialAPI data from the UART before sending and ACKs to clear any retries.
        '''
        time.sleep(.1)
        if self.UZB.in_waiting: 
            self.UZB.write(ACK)  # ACK just to clear out any retries
            if DEBUG>5: print("Dumping ", end='')
        while self.UZB.in_waiting: # purge UART RX to remove any old frames we don't want
            c=self.UZB.read()
            if DEBUG>5: print("{:02X}".format(c), end='', flush=True)
        frame = bytes([len(SerialAPIcmd)+2]) + REQUEST + SerialAPIcmd # add LEN and REQ bytes which are part of the checksum
        chksum= self.checksum(frame)
        pkt = SOF + frame + chksum # add SOF to front and CHECKSUM to end
        if DEBUG>8: print("pkt={}".format(''.join("%02x " % b for b in pkt)))
        for retries in range(1,4):                        # retry up to 3 times. Z-Wave traffic often causes the UART to lose the SOF and drop the frame.
            self.UZB.write(pkt)  # send the command
            #if DEBUG>9: print("Sending ", end='')
            #for c in pkt:
            #    if DEBUG>9: print("{:02X},".format(c), end='', flush=True)
            #    self.UZB.write(c)  # send the command
            #if DEBUG>9: print(" ")
            # should always get an ACK/NAK/CAN so wait for it here
            c=self.GetRxChar(500) # wait for the ACK
            if c==None:
                if DEBUG>1: print("no ACK on try #{}".format(retries),flush=True)
                for i in range(32):
                    self.UZB.write(ACK)       # send ACKs to see if the LEN was incorrectly received 
                    if self.UZB.inWaiting(): break      # if we get an ACK/NAK/CAN then stop sending ACKs and retry
            elif c==ACK:                       # then the frame is OK so no need to retry
                break
            elif c!=ACK:                       # didn't expect this so just retry
                if DEBUG>1: print("Error - not ACKed = 0x{:02X}".format(c))
                self.UZB.write(ACK)                 # send an ACK to try clear out whatever the problem might be
                while self.UZB.in_waiting:         # purge UART RX to remove any old frames we don't want
                    c=self.UZB.read()
        if retries>1 and DEBUG>5:
            print("Took {} tries".format(retries))
        response=None
        if returnStringFlag:    # wait for the returning frame for up to 5 seconds
            response=self.GetZWave(timeout)    
        return response
            
    def PrintVersion(self):
        ''' Examine the controller and retrieve the version number and a few other bits of info '''
        pkt=self.Send2ZWave(FUNC_ID_SERIAL_API_GET_CAPABILITIES,True)
        if pkt==None:
            print("Unable to get SerialAPI capabilities - exiting")
            exit()
        (ver, rev, man_id, man_prod_type, man_prod_type_id, supported) = unpack("!2B3H32s", pkt[1:])
        print("SerialAPI Ver={0}.{1}".format(ver,rev))   # SerialAPI version is different than the SDK version
        print("Mfg={:04X}".format(man_id),end='')
        if man_id==0: 
            print(" Silicon Labs")
        else:
            print("")
        print("ProdID/TypeID={0:02X}:{1:02X}".format(man_prod_type,man_prod_type_id))
        pkt=self.Send2ZWave(FUNC_ID_ZW_GET_VERSION,True)  # SDK version
        (VerStr, lib) = unpack("!12sB", pkt[1:])
        VersionKey=VerStr[-5:-1]
        if VersionKey in ZWAVE_VER_DECODE:
            print("{} = {}".format(VerStr,ZWAVE_VER_DECODE[VersionKey]))
        else:
            print("Z-Wave version unknown = {}".format(VerStr))
        print("Library={} {}".format(lib,libType[lib]))
        pkt=self.Send2ZWave(FUNC_ID_SERIAL_API_GET_INIT_DATA,True)
        if pkt!=None and len(pkt)>33:
            print("NodeIDs=", end='')
            for k in range(4,28+4):
                j=pkt[k] # this is the first 8 nodes
                for i in range(0,8):
                    if (1<<i)&j:
                        print("{},".format(i+1+ 8*(k-4)),end='')
            print(" ",flush=True)

    def FetchNVM(self):
        ''' Read the NVM and return an IntelHex (self.NVM) filled with the data
        Only the first 16K bytes are read out which is where the network information is stored.
        '''
        bufsize=128
        addr=0
        print("Working ", end='')
        for index in range(0,16*1024,bufsize):
            pkt=self.Send2ZWave(FUNC_ID_NVM_EXT_READ_LONG_BUFFER + b'\x00' + bytes([int(index/256)]) + bytes([index%256]) +b'\x00' + bytes([bufsize]) ,True) # appears the largest buffer you can ask for is about 128 bytes
            for i in range(1,bufsize+1):
                self.NVM[addr]=pkt[i]
                addr+=1
            print(".",end='',flush=True)        
        print(" done")

    def usage():
        print("")
        print("Usage: python ZWaveNVM500.py [COMxx]")
        print("COMxx is the Z-Wave UART interface - typically COMxx for windows and /dev/ttyXXXX for Linux")
        print("Reads the first 16KB of the EEPROM and saves it to the file NVM.hex ")
        print("Version {}".format(VERSION))
        print("")

if __name__ == "__main__":
    ''' Start the app if this file is executed'''
    try:
        self=ZWaveNVM500()
    except:
        print('error - unable to start program')
        ZWaveNVM500.usage()
        exit()

    # fetch and display various attributes of the Controller - these are not required but are handy
    self.PrintVersion()
    self.FetchNVM()     # read the data out of the NVM
    try:
        self.NVM.write_hex_file(self.filename)      # Write the hex file out
    except:
        print("Failed to write the hex file:{}".format(self.filename))

    exit()
