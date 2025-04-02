'''
Program 1 - Pinger assignment
COSC370
Logan Kelsch
3/9/2025 - 3/17/2025
The skeleton of this file was NOT coded by me. The skeleton of this file was derived from
the student resource section of this book, under 'Python 3 Socket Programming Assignment'.

IMPORTANT:
A '#NOTE BEGIN/END LOGAN'S ADDITION END#NOTE' is added 
into the program at all locations where I added onto the initial file.
'''

from socket import *
import os
import struct
import time
import select
import sys

ICMP_ECHO_REQUEST = 8

def checksum(string):

	if(isinstance(string, str)):
		string.encode()

	csum = 0
	countTo = (len(string) // 2) * 2
	count = 0

	while count < countTo:
		thisVal = string[count + 1] * 256 + string[count]
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
			return None, "Request timed out."

		timeReceived = time.time()
		recPacket, addr = mySocket.recvfrom(1024)

		#NOTE BEGIN LOGAN'S ADDITION END#NOTE

		#check to ensure the length of the packet coming in is correct
		#packet size should be 20+8
		if(len(recPacket)<28):
			return None, "Packet too short."
		
		#extract ICMP header
		icmp_header = recPacket[20:28]
		icmp_type, icmp_code, icmp_checksum, packetID, sequence = struct.unpack("bbHHh", icmp_header)


		# Validate the ICMP Response 
		if(icmp_type != 0):
			# Interpret ICMP Error Code
			if icmp_type == 3:
				if icmp_code == 0:
					return None, "Destination Network Unreachable"
				elif icmp_code == 1:
					return None, "Destination Host Unreachable"
				else:
					return None, f"Destination Unreachable, code {icmp_code}"
		elif packetID != ID:
			return None, "Packet ID does not match, ignoring."
		
		# Ensure the packet has enough bytes for a timestamp
		if len(recPacket) < 28 + struct.calcsize("d"):
			return None, "Received packet does not contain a valid timestamp"
		
		# Extract the timestamp and compute RTT (in ms)
		timeSent = struct.unpack("d", recPacket[28:28 + struct.calcsize("d")])[0]  # Extracting the timestamp
		rtt = (timeReceived - timeSent) * 1000  # Computing RTT & converting to ms
		
		# Ensure time elasped doesn't cause timeout
		timeLeft = timeLeft - howLongInSelect
		if timeLeft <= 0:
			return rtt, "Request timed out when receiving."
		
		#NOTE BEGIN LOGAN'S ADDITION END#NOTE

		#return the original message, as well as the raw RTT data
		return rtt, f"Reply from {destAddr}: time={rtt}ms"
	
		#NOTE END LOGAN'S ADDITION END#NOTE

def sendOnePing(mySocket, destAddr, ID):
	# Header is type (8), code (8), checksum (16), id (16), sequence (16)
	myChecksum = 0

	#NOTE BEGIN LOGAN'S ADDITION END#NOTE

	#struct - interpret strings as packed binary data
	header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
	data = struct.pack("d", time.time())

	#NOTE END LOGAN'S ADDITION END#NOTE

	# Calculate the checksum on the data and the dummy header.
	myChecksum = checksum(header + data)
	
	# Get the right checksum, and put in the header
	if sys.platform == 'darwin':
		# Convert 16-bit integers from host to network byte order
		myChecksum = htons(myChecksum) & 0xffff
	else:
		myChecksum = htons(myChecksum)
	
	#NOTE BEGIN LOGAN'S ADDITION END#NOTE

	#pack header information with bbHHh format
	header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
	
	#combine data into packet variable
	packet = header + data
	
	#send packet
	mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str

	#NOTE END LOGAN'S ADDITION END#NOTE

def doOnePing(destAddr, timeout):
	icmp = getprotobyname("icmp")
	# SOCK_RAW is a powerful socket type
	mySocket = socket(AF_INET, SOCK_RAW, icmp)
	myID = os.getpid() & 0xFFFF  # Return the current process ID

	sendOnePing(mySocket, destAddr, myID)

	#NOTE BEGIN LOGAN'S ADDITION END#NOTE

	#collect returns from receive function, INCLUDING raw RTT
	rtt, delay = receiveOnePing(mySocket, myID, timeout, destAddr)

	mySocket.close()
	
	#then return both values received from receiver function
	#after closing the socket
	return rtt, delay

	#NOTE END LOGAN'S ADDITION END#NOTE

def ping(
	host	:	str	=	"127.0.0.1", 
	num_pings:	int	=	10000,
	timeout	:	float	=	1,
	sleep	:	float	=	1
):
	# timeout=1 means: If one second goes by without a reply from the server,
	# the client assumes that either the client's ping or the server's pong is lost
	dest = gethostbyname(host)
	print("Pinging " + dest + " using Python:")
	print("")

	#NOTE BEGIN LOGAN'S ADDITION END#NOTE

	#variable to collect total of tallies
	ping_tally = 0

	#variable to collect all RTTs
	collected_rtt = []

	# Send ping requests to a server separated by approximately one second
	for i in range(num_pings):

		#collect raw RTT and delay string from one ping function
		rtt, delay = doOnePing(dest, timeout)
		#tally up for pings complete
		ping_tally+=1
		#ensure raw RTT is interpretable, jitter stays logical if not appended.
		if(rtt != None):
			collected_rtt.append(rtt)
		#show original delay string to user
		print(delay)
		#sleep for desired time
		time.sleep(sleep)  # one second

	#cannot collect sufficient data with less than 2 pings. output nothing
	if(ping_tally < 2):
		raise ValueError(f"Insufficient data can be collected with {ping_tally} pings.")

	#collect jitter information
	tot_jit = 0
	for i in range(1, len(collected_rtt)):
		#collect differences in each RTT
		tot_jit+=abs(collected_rtt[i-1]-collected_rtt[i])

	#output all calucated datapoints
	print(f"\nAVG RTT: {round(sum(collected_rtt)/len(collected_rtt), 4)} ms")
	print(f"TOT RTT: {round(sum(collected_rtt), 4)} ms ({len(collected_rtt)} RTTs)")
	print(f"MAX RTT: {round(max(collected_rtt), 4)} ms")
	print(f"MIN RTT: {round(min(collected_rtt), 4)} ms")
	print(f"LOSS: {round(((ping_tally-len(collected_rtt))/ping_tally) * 100, 4)}%")
	print(f"JITTER: {round( tot_jit / (len(collected_rtt)-1) , 4)} ms")

	#NOTE END LOGAN'S ADDITION END#NOTE

	return delay


#NOTE BEGIN LOGAN'S ADDITION END#NOTE

#having difficulty running this with admin capabilities in a jupyter notebook.
#attempting to make this script executable from CL
if __name__ == "__main__":

	#set some default values for the pinger kwargs
	ping_kwargs = {
		'host'		:	"127.0.0.1",
		'timeout'	:	1,
		'num_pings'	:	5,
		'sleep'		:	1
	}

	#mapping flags to desired kwargs and casting types
	flag_map = {
		'-h'	:	{'arg':'host',		'type':str},
		'-t'	:	{'arg':'timeout',	'type':float},
		'-n'	:	{'arg':'num_pings',	'type':int},
		'-s'	:	{'arg':'sleep',		'type':float}
	}

	#helpful output upon arg errors that shows flag and format hints
	syntax_err_out = ValueError(
		f"\n\nArgument count is not allowed in its provided format.\n"
		f"\nPlease use the format as follows:\n\tFlags:\n\t\t-h\thost (IP or Name)"
		f"\n\t\t-t\ttimeout\n\t\t-n\tnumber of pings\n\t\t-s\tsleep timer (between pings)\n"
		f"\nPlease follow each flag with the desired value.\n"
	)

	#NOTE begin argument dissector

	#if command line arguments were received
	if(len(sys.argv)>1):
		
		#if only one argument was received, interpret as host variable
		if(len(sys.argv) == 2):

			#sys.argv comes in as string, can immediately assign
			ping_kwargs['host'] = sys.argv[1]

		#more than one argument was recieved
		else:

			#can only be interpreted as flag-value pairs, 
			#therefore ensure arg shaping
			if(len(sys.argv)%2==0):
				raise syntax_err_out

			#for each flag-value pair, interpret said pair
			for arg in range(int((len(sys.argv)-1)/2)):

				#using a try except statement for easy code condensing
				#take given flag and assign respective value as respective datatype
				try:
					#nothing prettier than a one-liner.
					#ASSIGN       from this flag          the kwarg =     CAST      this flag type       to value after flag
					ping_kwargs[flag_map[sys.argv[1+arg*2]]['arg']] = flag_map[sys.argv[1+arg*2]]['type'](sys.argv[2+arg*2])

				#this could arrise from illegal flag or illegal value
				#either of which, this output will suffice.
				except Exception as e:
					raise syntax_err_out

	#all arguments from here are fully interpreted and functional, can execute.
	ping(**ping_kwargs)

#NOTE END LOGAN'S ADDITION END#NOTE