''' Z-Wave 700 Series Product RF Test Generator

    This program is provided AS-IS without support.
    Feel free to copy and improve!

    Usage: python ProdTestGen.py [COM#]

    Requires Python3 and the Serial Library (https://github.com/pyserial/pyserial)

    Description: This program is similar to the Z-Wave 500 series sample application "ProdTestGen".
    This program requires a 700 series WSTK DevKit which has been programmed with the RailTest application.
    RailTest connects to a PC via USB and opens a COM port at 115200 baud.
    This program sends a series of RailTest commands to put the WSTK into a mode to do a quick RF production test.
    When the program is started, it waits for a NIF to be received from the DUT.
    The DUT will send a NIF typically when entering LEARN mode to join a Z-Wave network.
    It is NOT necessary for the DUT to join the Z-Wave network which would take several seconds to complete.
    When the NIF has been captured, ten NOPs will be sent to the DUT and the number of ACKs received is returned.
    The number of ACKs is printed.
    Less than 9 ACKed is considered a failure. You should get all 10 most of the time.

    The advantage of this test mode is:
    1) Does not require a lengthy Z-Wave Inclusion/Exclusion (typically about 10s)
    2) Test stations can be adjacent to each other without the need of RF shielding between them
       It is recommended there be at least a few meters between them
       Since there is no Inclusion/Exclusion they do not interfere with each other
       The search for a NIF should be enabled for only a few seconds when the DUT is activated to send a NIF to avoid interference with adjacent stations
    3) The test takes less than 2 seconds (the Z-Wave traffic takes 700ms)
    4) The RF is tested using the DUT application firmware using the application settings for RF power

    Future Enhancements:
    1) Drop the RF power to a fairly low level for half of the frames and maybe even way down for the last one to capture statistics and possibly look for calibration errors
    2) Detect a BEAM and do some calibration checking for the accuracy of the crystal
    3) Change this from a Python program to a command inside RailTest to perform the same function
    4) Add a check of the RSSI in the NIF and only accept ones that are very high
    5) Command line option to assume RailTest is already setup and just quickly check for NIF and send NOPs (would reduce the UART traffic but will it save time?)
    6) Can a Power NOP be sent and acked instead of just a regular NOP to lower the TX power of the NOP and the ACK?
    7) Return RSSI statistics which may also be useful for Pass/Fail criteria or manufacturing statistics

    Theory of Operation:
    The DUT is assumed to be a 700 series Z-Wave chip or later using at least SDK 7.13.1 (earlier versions did not ACK the NOP)
    The WSTK with RailTest on it is within 1m of the DUT
    Connection between the DUT and the WSTK could be with cables but it is recommended to use the antenna for a more complete functional test
    When the program is started it initializes the WSTK and checks the version of RailTest.
    Railtest is initialized to Z-Wave mode
    The program then waits for a NIF to arrive
    When the NIF is captured the HOMEID in the frame is extracted
    The program then sends 10 NOPs to the DUT of that HomeID. Note that the NodeID is zero if the node is not included in a network.
    Each DUT generates a random HomeID when it is not included in a network. That's why the HomeID has to be captured using this program.
    The ACKs for each NOP are filtered and counted.
    The number of ACKs is printed and the program can be used as a PASS/FAIL criteria.

    Author: Eric Ryherd - drzwave@silabs.com
    Date: 9/30/2020
'''

import serial           # serial port utilities
import sys
import time
import os

VERSION     = "0.9 - 10/1/2020"
DEBUG       = 1        # [0-10] higher values print more messages during debug

COMPORT     = "COM13"   # default COM port when running on a Windows PC
#COMPORT    = "/dev/ttyAMA0"    # default serial port on a Raspberry Pi

class ProdTestGen():
    def __init__(self):
        ''' Production Test Generator for 700 series Z-Wave chips
            Waits for DUT to send NIF, then sends 10 NOPs and returns the number of ACKs
        '''
        self.COMPORT=COMPORT
        if DEBUG>3: print("COM Port set to {}".format(self.COMPORT))
        try:
            self.com= serial.Serial(self.COMPORT,'115200',timeout=1)
        except Exception as err:
            print("Unable to open serial port {} Error={}".format(self.COMPORT,err))
            exit()

    def ReadCOM(self):
        ''' Read from the serial port until a CRLF is found and return all the bytes
            It is possible to return an empty string if the timeout passes without any characters arriving 
        '''
        line=b""
        if not self.com.in_waiting: # calling ReadCOM implies chars are expected but if none wait a bit
            time.sleep(.1)
        while self.com.in_waiting:
            c=self.com.read()
            if c==b'\r' or c==b'\n':
                if len(line)>=1:    # drop CRLF chars at the start of a line
                    break
            else:
                line+=c   
            if not self.com.in_waiting: # sometimes there is a pause in the middle of a line - this delay waits for a few character times for more to arrive
                time.sleep(.05)
        return(line)


    def GetVersion(self):
        ''' Return the version of RailTest 
        Railtest will return something like this:
        {{(getVersion)}{App:2.8.6}{RAIL:2.8.6}{Multiprotocol:False}{Built:Jun  4 2020 10:55:56}}
        this function will return the string "RAIL:2.8.6" or a string of len=0 if not found
        '''
        self.com.write(b"\r\ngetVersion\n")
        time.sleep(0.1)
        line=b""
        retries=5
        while b'getVersion' not in line:
            line=self.ReadCOM()
            retries-=1
            if retries<0:
                return("FAILED to get Railtest Version")
        temp=line.split(b'}')
        for i in temp:
            if b"RAIL" in i:
                line=i[1:]
        if DEBUG>1: print("RailTest Version {}".format(line.decode("utf-8")),flush=True)
        return(line)

    def SendRailCmd(self, cmd=b"help", response=b""):
        ''' Send a RailTest command over the serial port to the chip running Rail.
            Checks that the command was received properly and will retry it once with a pause if there was an error.
            Sometimes if a string of commands are sent quickly the UART buffers overflow and the command is corrupted.
            This function will check that the command was sent OK.
            cmd=ASCI string of the railtest command - CRLF will be added to the end
            response=ASCI string of the expected reponse
        '''
        self.com.write(cmd+b"\n")
        line=self.ReadCOM()
        if DEBUG>9: print(line,flush=True)
        if b"{error:" in line: # command failed so try 1 more time after a pause
            time.sleep(.1)
            if DEBUG>5: print("Retry 1" + cmd)
            self.com.write(cmd+b"\n")
            line=self.ReadCOM()
        if len(response)>0 and response not in line:
            time.sleep(.1)
            if DEBUG>5: print("Retry 2" + cmd)
            self.com.write(cmd+b"\n")

    def Setup4Rx(self):
        ''' Setup Railtest for Z-Wave Receive ready to capture up the NIF '''
        self.SendRailCmd(b"rx 0")
        self.SendRailCmd(b"setZWaveMode 1 3",b"{ZWAVE:Enabled}")       # NOTE! You may need to customize these for your specific region
        self.SendRailCmd(b"setZWaveRegion 1")       # EU=0, US=1, ANZ=2, HK=3, IN=5, IL=6, RU=7, CN=8 others are in ZW_radio_api.h
        self.SendRailCmd(b"setChannel 2")           # 2=9.6K, 1=40K, 0=100K for 2 channel systems - this would need to change for 3ch regions - NIFs are normally sent using 9.6K
        self.SendRailCmd(b"setTxPayload 4 0x01 0x41 0x06 0x0c 0x00") # 4=SourceNodeID, 5=Prop1, 6=Prop2, 7=Length, 8=Dest NodeID - the checksum is computed by RailTest but the length has to include 2 bytes for 100K
        self.SendRailCmd(b"setTxLength 20")         # sets the length of the TX buffer - frames we send a short
        self.SendRailCmd(b"setTxDelay 30")          # ms between NOPs - need enough time between to get the ACKs but fast enough to finish quickly
        self.SendRailCmd(b"setpower -130")          # lower the power to roughly the minimum
        self.com.reset_input_buffer()               # dump the echos of all the commands
        
    def IsNIF(line):
        ''' Returns True if the packet in LINE contains a NIF otherwise False '''
        if line==None:
            return(False)
        if b'len:' not in line:
            return(False)
        line2=line.decode('utf-8')
        linesplit = line2.split('}') 
        length=0
        for i in linesplit:                 # sometimes several payloads are in one line but capture just the 1st one
            if length==0 and 'len:' in i:
                length=int(i.split(':')[1])
            if 'payload:' in i:
                payload = i.split()
                payload.remove(payload[0])  # remove "{payload:" and leave just the bytes of data in hex
                break
        if DEBUG>9:print("len={}".format(length),flush=True)
        if DEBUG>9:print("payload={}".format(payload))
        if payload==None or len(payload)<15: # NIF has to be at least 15 bytes long
            return(False)
        if payload[9]!="0x01" or payload[10]!="0x01":   # CC=Protocol, CMD=NIF
            return(False)
        # TODO - add a check of the RSSI and if not high enough then return False. The DUT is assumed to be within a fraction of a meter so RSSI should be max. This check should help reject adjacent test station NIFs.
        return(True)

    def SendNOPs(self,line):
        ''' Send 10 NOPs and return the number of ACKs
            NOP frame is:
            Byte #  Data    Description
            0       HH      HomeID
            1       HH      HomeID
            2       HH      HomeID
            3       HH      HomeID
            4       01      Source NodeID        
            5       41      Properties 1
            6       06      Properties 2
            7       0B      Length
            8       ID      Destination NodeID
            9       00      NOP command
            line is the NIF as returned by RailTest - it is parsed to get the HomeID
        '''
        linesplit = line.split(b'}')        # extract the HomeID from the NIF
        length=0
        for i in linesplit:                 # sometimes several payloads are in one line but capture just the 1st one
            if length==0 and b'len:' in i:
                length=int(i.split(b':')[1])
            if b'payload:' in i:
                payload = i.split(b' ')
                payload.remove(payload[0])  # remove "{payload:" and leave just the bytes of data in hex
                break
        self.com.write(b"setTxPayload 0 "+payload[0]+b" "+ payload[1]+b" "+ payload[2]+b" "+ payload[3]+b" 0x01 0x41 0x06 0x0b "+payload[4]+b" 0x00\r\n")
        self.HomeID = [payload[0], payload[1], payload[2], payload[3]]
        self.com.write(b"tx 10\r\n ")   # send 10 NOPs to the DUT
        acks=0
        timeout=0
        while acks<10 and timeout<30:   # count the ACKs from the DUT
            timeout+=1
            line=self.ReadCOM()
            if b"rxPacket" in line and b"payload" in line:
                linesplit = line.split(b'}')
                for i in linesplit:
                    if b"payload" in i:
                        payload = i.split(b' ')
                        payload.remove(payload[0])
                        if payload[0]==self.HomeID[0] and payload[1]==self.HomeID[1] and payload[2]==self.HomeID[2] and payload[3]==self.HomeID[3] and payload[5]==b"0x03":
                            acks+=1
                        break
            if DEBUG>5: print("acks={} line={}".format(acks,line),flush=True)
        return(acks)

    def usage():
        print("")
        print("Usage: python ProdTestGen.py [COMxx]")
        print("Version {}".format(VERSION))
        print("COMxx is the Z-Wave UART interface - typically COMxx for windows and /dev/ttyXXXX for Linux")
        print("Change the COMPORT variable in code to make yours the default")
        print("Once the program is running, it is waiting for a NIF to arrive")
        print("When the NIF arrives, it will send 10 NOPs to the DUT and print out the number of ACKs")
        print("If the ACKs are above 8, ship it!")
        print("")


if __name__ == "__main__":
    ''' Start the app if this file is executed'''

    if len(sys.argv)>1:
        COMPORT=sys.argv[1]
    try:
        self=ProdTestGen()       # open the serial port to the UZB or Z-Wave interface
    except:
        print('error - unable to start program')
        ProdTestGen.usage()
        exit()

    if DEBUG>8: print("Serial port {} opened".format(COMPORT))

    version=self.GetVersion()
    # TODO check for the proper version here

    self.Setup4Rx()                     # setup for Z-Wave

    self.SendRailCmd(b"rx 1")           # Turn on receiver and wait for the NIF

    # look for a frame that looks like:  {{(rxPacket)}{len:30}{timeUs:485687680}{timePos:4}{crc:Pass}{rssi:-22}{lqi:104}{phy:0}{isAck:False}{syncWordId:0}{antenna:0}{channelHopIdx:254}{payload: 0xe1 0xd6 0x94 0xc4 0x00 0x01 0x06 0x1f 0xff 0x01 0x01 0xd3 0x9c 0x01 0x10 0x01 0x5e 0x56 0x86 0x72 0x5a 0x85 0x59 0x73 0x25 0x27 0x70 0x2c 0x2b 0x7a}}
    #Byte #	Data	Description
    #0-3       E1D694C4	HomeID
    #4	        00	Source NodeID which is zero meaning the node is not in a network
    #5	        01	Prop1 - Header type, speed, lowpwr, Ack, routed
    #6	        01	Prop2 - sequence #01, beam, suc
    #7	        1F	Length
    #8	        FF	Destination FF=broadcast
    #9	        01	Protocol CC
    #10	        01	NIF
    #11	        D3	Prop1 - Security, controller, beam, 250ms, 1s, optional func
    #12	        9C	Prop2 - Protocol version, routing, listening
    #13	        01	Prop3 - speed extensions = 100K
    #14	        10	Generic Device Class - SWITCH_BINARY
    #15	        01	Specific Device Class - Power switch binary
    #17-n		command classes
    # 

    try:
        if DEBUG>=1: print("Waiting for NIF - trigger DUT to enter Learn Mode", flush=True)
        while True:                     # look for NIFs or <CTL-C>
            if self.com.in_waiting:
                line = self.ReadCOM()
                if DEBUG>7: print(line)
                if b"rxPacket" not in line:
                    continue
                if ProdTestGen.IsNIF(line):
                    if DEBUG>7: print("NIF=",line)
                    break
            time.sleep(.1)
    except KeyboardInterrupt:
        print("Exit")
        exit()

    acks=self.SendNOPs(line)            # pull the HomeID/NodeID from the NIF and send 10NOPs and return the number of ACKs

    print("ACKs={}".format(acks))

    self.com.write(b"rx 0\r\n")         # Turn OFF receiver
    exit()
    
