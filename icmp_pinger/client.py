'''
Program 1 - Pinger assignment - COSC370
Logan Kelsch - 3/9/2025
The skeleton of this file was NOT coded by me. The skeleton of this file was derived from
the student resource section of this book, under 'Python 3 Socket Programming Assignment'.
A '#NOTE BEGIN/END LOGAN'S ADDITION END#NOTE' is added at the program at my added locations.
'''

from socket import *
import os
import sys
import struct
import time
import select
import numpy as np

ICMP_ECHO_REQUEST = 8



#variable to collect all RTTs
collected_rtt = []

#ADDTN
all_rtt = []

def checksum(string):
	csum = 0
	countTo = (len(string) // 2) * 2
	count = 0

	while count < countTo:
		thisVal = ord(string[count + 1]) * 256 + ord(string[count])
		csum = csum + thisVal
		csum = csum & 0xffffffff
		count = count + 2

	if countTo < len(string):
		csum = csum + ord(string[len(string) - 1])
		csum = csum & 0xffffffff

	csum = (csum >> 16) + (csum & 0xffff)
	csum = csum + (csum >> 16)
	answer = ~csum
	answer = answer & 0xffff
	answer = answer >> 8 | (answer << 8 & 0xff00)

	return answer

def receiveOnePing(mySocket, ID, timeout, destAddr):
	timeLeft = timeout

	while True:
		startedSelect = time.time()
		whatReady = select.select([mySocket], [], [], timeLeft)
		howLongInSelect = (time.time() - startedSelect)

		if whatReady[0] == []:  # Timeout
			return "Request timed out."

		timeReceived = time.time()
		recPacket, addr = mySocket.recvfrom(1024)

		#NOTE BEGIN LOGAN'S ADDITION END#NOTE

		#check to ensure the length of the packet coming in is correct
		#packet size should be 20+8
		if(len(recPacket)<28):
			return "Packet too short."
		
		#extract ICMP header
		icmp_header = recPacket[20:28]
		icmp_type, icmp_code, icmp_checksum, packetID, sequence = struct.unpack("bbHHh", icmp_header)


		# Validate the ICMP Response 
		if(icmp_type != 0):
			# Interpret ICMP Error Code
			if icmp_type == 3:
				if icmp_code == 0:
					return "Destination Network Unreachable"
				elif icmp_code == 1:
					return "Destination Host Unreachable"
				else:
					return f"Destination Unreachable, code {icmp_code}"
		elif packetID != ID:
			return "Packet ID does not match, ignoring."
		
		# Ensure the packet has enough bytes for a timestamp
		if len(recPacket) < 28 + struct.calcsize("d"):
			return "Received packet does not contain a valid timestamp"
		
		# Extract the timestamp and compute RTT (in ms)
		timeSent = struct.unpack("d", recPacket[28:28 + struct.calcsize("d")])[0]  # Extracting the timestamp
		rtt = (timeReceived - timeSent) * 1000  # Computing RTT & converting to ms
		
		# Ensure time elasped doesn't cause timeout
		timeLeft = timeLeft - howLongInSelect
		if timeLeft <= 0:
			return "Request timed out when receiving."
		
		# Update RTTs (total, min, max)
		collected_rtt.append(rtt)
		
		# Return message containing rtt
		return f"Reply from {destAddr}: time={rtt}ms"

def sendOnePing(mySocket, destAddr, ID):
	# Header is type (8), code (8), checksum (16), id (16), sequence (16)
	myChecksum = 0

	# Make a dummy header with a 0 checksum
	# struct -- Interpret strings as packed binary data
	header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
	data = struct.pack("d", time.time())

	# Calculate the checksum on the data and the dummy header.
	myChecksum = checksum(str(header + data))

	# Get the right checksum, and put in the header
	if sys.platform == 'darwin':
		# Convert 16-bit integers from host to network byte order
		myChecksum = htons(myChecksum) & 0xffff
	else:
		myChecksum = htons(myChecksum)

	header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
	packet = header + data
	mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str

def doOnePing(destAddr, timeout):
	icmp = getprotobyname("icmp")
	# SOCK_RAW is a powerful socket type
	mySocket = socket(AF_INET, SOCK_RAW, icmp)
	myID = os.getpid() & 0xFFFF  # Return the current process ID

	sendOnePing(mySocket, destAddr, myID)
	delay = receiveOnePing(mySocket, myID, timeout, destAddr)

	mySocket.close()
	return delay

def ping(host, timeout=1):
	# timeout=1 means: If one second goes by without a reply from the server,
	# the client assumes that either the client's ping or the server's pong is lost
	dest = gethostbyname(host)
	print("Pinging " + dest + " using Python:")
	print("")

	#variable to collect total of tallies
	ping_tally = 0

	# Send ping requests to a server separated by approximately one second
	while True:
		delay = doOnePing(dest, timeout)
		ping_tally+=1
		print(delay)
		time.sleep(1)  # one second
	return delay


#having difficulty running this with admin capabilities in a jupyter notebook.
#attempting to make this script executable from CL
if __name__ == "__main__":

	ping("127.0.0.1")