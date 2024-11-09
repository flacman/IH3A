import threading
import queue
import socket
import sys
import logging
import argparse
import re

from enum import Enum
from SharedMemLib import Mode, read_write_sharedMem



# Function to parse a syslog message sent by OSSEC and return a dictionary with the parsed fields
# message: Syslog message to parse
# Returns: Dictionary with the parsed fields, or None if the message is not in OSSEC format
def parse_ossec_message(message):
    ossec_pattern = re.compile(
        r'<(?P<priority>\d+)>(?P<timestamp>\S+ \d+ \d+:\d+:\d+) (?P<hostname>\S+) (?P<process>\S+)(?:\[(?P<pid>\d+)\])?: '
        r'(?P<rule_id>\d+): (?P<level>\d+): (?P<description>.+) - (?P<message>.+)'
    )
    match = ossec_pattern.match(message)
    if match:
        priority = int(match.group('priority'))
        facility = priority // 8
        severity = priority % 8
        timestamp = match.group('timestamp')
        hostname = match.group('hostname')
        process = match.group('process')
        pid = match.group('pid')
        rule_id = match.group('rule_id')
        level = match.group('level')
        description = match.group('description')
        message_content = match.group('message')
        return {
            'type': 'ossec',
            'facility': facility,
            'severity': severity,
            'timestamp': timestamp,
            'hostname': hostname,
            'process': process,
            'pid': pid,
            'rule_id': rule_id,
            'level': level,
            'description': description,
            'message': message_content
        }
    return None

# Function to parse a syslog message sent by Suricata and return a dictionary with the parsed fields
# message: Syslog message to parse
# Returns: Dictionary with the parsed fields, or None if the message is not in Suricata format

def parse_suricata_message(message):
    suricata_pattern = re.compile(
        r'<(?P<priority>\d+)>'           # Priority
        r'(?P<version>\d+) '             # Version
        r'(?P<timestamp>[^ ]+) '         # Timestamp
        r'(?P<hostname>[^ ]+) '          # Hostname
        r'(?P<app_name>[^ ]+) '          # App name
        r'(?P<procid>[^ ]+) '            # Proc ID
        r'(?P<msgid>[^ ]+) '             # Msg ID
        r'(?P<structured_data>-|(\[.*?\])) '  # Structured data
        r'(?P<message>.+)'               # Message
    )
    match = suricata_pattern.match(message)
    if match:
        priority = int(match.group('priority'))
        facility = priority // 8
        severity = priority % 8
        return {
            'type': 'suricata',
            'facility': facility,
            'severity': severity,
            'version': match.group('version'),
            'timestamp': match.group('timestamp'),
            'hostname': match.group('hostname'),
            'app_name': match.group('app_name'),
            'procid': match.group('procid'),
            'msgid': match.group('msgid'),
            'structured_data': match.group('structured_data'),
            'message': match.group('message')
        }
    return None

# Function to parse a syslog message sent by ModSecurity and return a dictionary with the parsed fields
# message: Syslog message to parse
# Returns: Dictionary with the parsed fields, or None if the message is not in ModSecurity format

def parse_modsecurity_message(message):
    modsecurity_pattern = re.compile(
    r'<(?P<priority>\d+)>1 (?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+\d{2}:\d{2}) (?P<hostname>\S+) (?P<app_name>\S+) - - - (?P<message_content>.+)'
    )
    match = modsecurity_pattern.match(message)
    if match:
        priority = int(match.group('priority'))
        facility = priority // 8
        severity = priority % 8
        timestamp = match.group('timestamp')
        hostname = match.group('hostname')
        app_name = match.group('app_name')
        #transaction_id = match.group('transaction_id')
        message_content = match.group('message_content')
        return {
            'type': 'modsecurity',
            'facility': facility,
            'severity': severity,
            'timestamp': timestamp,
            'hostname': hostname,
            'app_name': app_name,
            #'transaction_id': transaction_id,
            'message': message_content
        }
    return None
# Function to parse a syslog message and determine its format (OSSEC, Suricata, or ModSecurity)
# message: Syslog message to parse
# Returns: Dictionary with the parsed fields, or None if the message is not in any of the supported formats

def parse_syslog_message(message):
    # Try parsing with each parser
    parsers = [parse_ossec_message, parse_suricata_message, parse_modsecurity_message]
    for parser in parsers:
        parsed_message = parser(message)
        if parsed_message:
            return parsed_message
    logging.error(f"Failed to parse message: {message}")
    return None

def process_parsed_message(parsed_message):
    str_to_write = None
    if parsed_message['type'] == 'ossec':
        str_to_write = f"OSSEC - Facility: {parsed_message['facility']}, Severity: {parsed_message['severity']}, Timestamp: {parsed_message['timestamp']}, Hostname: {parsed_message['hostname']}, Process: {parsed_message['process']}, PID: {parsed_message['pid']}, Rule ID: {parsed_message['rule_id']}, Level: {parsed_message['level']}, Description: {parsed_message['description']}, Message: {parsed_message['message']}"
    elif parsed_message['type'] == 'suricata':
        str_to_write = f"Suricata - Facility: {parsed_message['facility']}, Severity: {parsed_message['severity']}, Version: {parsed_message['version']}, Timestamp: {parsed_message['timestamp']}, Hostname: {parsed_message['hostname']}, App Name: {parsed_message['app_name']}, Proc ID: {parsed_message['procid']}, Msg ID: {parsed_message['msgid']}, Structured Data: {parsed_message['structured_data']}, Message: {parsed_message['message']}"
    elif parsed_message['type'] == 'modsecurity':
        str_to_write = f"ModSecurity - Facility: {parsed_message['facility']}, Severity: {parsed_message['severity']}, Timestamp: {parsed_message['timestamp']}, Hostname: {parsed_message['hostname']}, App Name: {parsed_message['app_name']}, Message: {parsed_message['message']}"

    if str_to_write:
        logging.info(str_to_write)
        read_write_sharedMem(Mode.WRITE, str_to_write)

def handle_message(message_queue):
    message_buffer = []  # Buffer to hold messages between '-A--' and '-Z--'
    collecting = False  # Flag to indicate if we are collecting messages

    while True:
        message = message_queue.get()
        if message is None:
            break

        message = message.strip()

        if '-A--' in message:
            # Start of a new message block
            collecting = True
            message_buffer = []  # Reset buffer
            mes = parse_modsecurity_message(message)
            if mes:
                message = mes['message'].replace('-A--', '').strip()
                message_buffer =mes
            # Remove '-A--' from the message
            #message = message.replace('-A--', '').strip()
            #if message:
            #    message_buffer.append(message)

        elif '-Z--' in message:
            # End of the current message block
            if collecting:
                # Remove '-Z--' from the message
                #mes = parse_modsecurity_message(message)
                #if mes:
                #    message = message['message'].replace('-Z--', '').strip()
                #    message_buffer.append(message)
                # Combine all buffered messages
                
                #full_message = '\n'.join(message_buffer.values())
                # Split into individual messages if needed
                
                process_parsed_message(message_buffer)
                # Reset buffer and collecting flag
                message_buffer = []
                collecting = False
            else:
                # Received '-Z--' without '-A--', ignore or log if necessary
                logging.warning("Received end marker '-Z--' without start marker '-A--'.")

        else:
            # Regular message content
            if collecting:
                mes = parse_modsecurity_message(message)
                if mes and message_buffer['message']:
                    message_buffer['message']+=""+mes['message']
            else:
                # Not collecting, ignore or handle as per requirements
                #logging.warning("Received message outside of '-A--' and '-Z--' markers.")
                process_parsed_message(parse_syslog_message(message))

        message_queue.task_done()

def main():
    parser = argparse.ArgumentParser(description="Syslog server")
    parser.add_argument('--ip', type=str, default="0.0.0.0", help="IP address to bind to")
    parser.add_argument('--port', type=int, default=514, help="Port to bind to")
    args = parser.parse_args()

    UDP_IP = args.ip
    UDP_PORT = args.port

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f"Starting syslog server on {UDP_IP}:{UDP_PORT}")

    message_queue = queue.Queue()
    threading.Thread(target=handle_message, args=(message_queue,), daemon=True).start()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((UDP_IP, UDP_PORT))
    except socket.error as e:
        logging.error(f"Failed to create or bind socket: {e}")
        sys.exit(1)

    logging.info(f"Listening for syslog messages on {UDP_IP}:{UDP_PORT}")

    try:
        while True:
            try:
                data, addr = sock.recvfrom(4096)  # Increased buffer size if needed
                message = data.decode('utf-8', errors='replace')
                message_queue.put(message)
            except (socket.error, UnicodeDecodeError) as e:
                logging.error(f"Failed to receive or decode message: {e}")
    except KeyboardInterrupt:
        logging.info("Syslog server stopped.")
    finally:
        sock.close()
        message_queue.put(None)  # Signal the message handler to exit
        message_queue.join()

if __name__ == "__main__":
    main()