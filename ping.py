import socket
import struct
import os
import time
import select

# ICMP header values
ECHO_REQUEST_TYPE, ECHO_REQUEST_CODE = 8, 0
ECHO_REPLY_TYPE, ECHO_REPLY_CODE = 0, 0
    
# ------ class definition starts ------
class Ping:
    def __init__(self, socket, dest_ip, ping_count, timeout):
        self.socket = socket
        self.dest_ip = dest_ip
        self.timeout = timeout
        self.ping_count = ping_count
        self.id = os.getpid()
        self.seq_num = 1

    def calculate_checksum(self, data):
        checksum = 0
        # Handle odd-length data
        if len(data) % 2 != 0:
            data += b"\x00"

        # Calculate checksum
        for i in range(0, len(data), 2):
            checksum += (data[i] << 8) + data[i+1]

        checksum = (checksum >> 16) + (checksum & 0xffff)
        checksum += checksum >> 16
        return (~checksum) & 0xffff

    def create_packet(self):
        checksum_val = 0 # initially set to zero
        payload = b'Hey there im an icmp ping'
        header = struct.pack(
            '!BBHHH', ECHO_REQUEST_TYPE, ECHO_REQUEST_CODE, checksum_val, self.id, self.seq_num
        )

        # Add checksum and reform the packet
        checksum_val = self.calculate_checksum(header + payload)
        header = struct.pack(
            '!BBHHH', ECHO_REQUEST_TYPE, ECHO_REQUEST_CODE, checksum_val, self.id, self.seq_num
        )

        self.id += 1 # increase id num for next packet
        return header + payload

    def ping_once(self):
        packet = self.create_packet()
        t_start = time.time()
        
        # Send ping
        self.socket.sendto(packet, (self.dest_ip, 15326))
        expected_timeout = t_start + self.timeout

        while(time.time() < expected_timeout):
            # Receive ping
            ready = select.select([self.socket], [], [], expected_timeout - time.time())
            if ready[0] == []:  # Timeout
                break
            t_end = time.time()

            # Parse response
            response, addr = self.socket.recvfrom(1024)
            icmp_header = response[20:28]  # The ICMP header starts after the IP header (first 20 bytes)
            icmp_type, icmp_code, icmp_checksum, icmp_id, icmp_seq = struct.unpack('!BBHHH', icmp_header)

            if (icmp_type == ECHO_REPLY_TYPE and icmp_code == ECHO_REPLY_CODE and icmp_seq == self.seq_num):
                return t_end - t_start
                
        return None # on timeout
    
# ------ class definition ends ------

def display_stats(dest_name, send_count, recv_count, min_time, max_time, tot_time):
    """
    Display ping stats on completion
    or on Ctrl+C interrupt
    """
    print("\n-----------------------------------")
    print(f"Ping statistics for {dest_name}:")

    # Preventing division by 0 errors
    if recv_count==0:
        print("\tNo packets were received\n")
        return

    lost = send_count - recv_count
    print(f"\tPackets: Sent = {send_count}, Received = {recv_count}, Lost = {lost} ({(100*lost)/(send_count)}% loss),")
    print("Approximate round trip times in milli-seconds:")
    print(f"\tMinimum = {int(min_time * 1000)}ms, Maximum = {int(max_time * 1000)}ms, Average = {int((tot_time * 1000)/recv_count)}ms\n")
    return

def verbose_ping(dest_name, timeout = 5.0, count = 5):
    # Get host ip
    try:
        dest_ip = socket.gethostbyname(dest_name)
    except:
        print("ERROR: Host does not exist.")
        exit(1)
    
    # Create socket object
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except:
        print("ERROR: Please run with admin/sudo permission.")
        exit(1)
    
    # Pinging begins
    print(f"--------- Pinging host {dest_ip} 64 bytes of data---------")

    ping = Ping(sock, dest_ip, ping_count=count, timeout=timeout)
    send_count = 0
    recv_count = 0
    min_time = 100
    max_time = 0
    tot_time = 0

    try:
        for _ in range(count):
            curr_time = ping.ping_once()
            send_count += 1
            
            if curr_time != None:
                print(f"64 bytes from {dest_ip}: time={int(curr_time*1000)} ms")
                recv_count += 1
                max_time = max(max_time, curr_time)
                min_time = min(min_time, curr_time)
                tot_time += curr_time
            else:
                print("Timeout fired, packet wasn't received.")
        # Display stats after all pings
        display_stats(dest_name, send_count, recv_count, min_time, max_time, tot_time)
        exit(0)
    except KeyboardInterrupt:
        display_stats(dest_name, send_count, recv_count, min_time, max_time, tot_time)
        exit(1)


if __name__ == '__main__':
    verbose_ping("google.com")
    # verbose_ping("a-test-url-that-is-not-available.com")
    # verbose_ping("127.0.0.1")
    
    
    