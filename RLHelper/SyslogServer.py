import threading
import queue
import socket
import sys
import logging
import argparse
import re

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

def parse_suricata_message(message):
    suricata_pattern = re.compile(
        r'<(?P<priority>\d+)>(?P<timestamp>\S+ \d+ \d+:\d+:\d+) (?P<hostname>\S+) suricata\[(?P<pid>\d+)\]: '
        r'(?P<event_type>\S+): (?P<message>.+)'
    )
    match = suricata_pattern.match(message)
    if match:
        priority = int(match.group('priority'))
        facility = priority // 8
        severity = priority % 8
        timestamp = match.group('timestamp')
        hostname = match.group('hostname')
        pid = match.group('pid')
        event_type = match.group('event_type')
        message_content = match.group('message')
        return {
            'type': 'suricata',
            'facility': facility,
            'severity': severity,
            'timestamp': timestamp,
            'hostname': hostname,
            'pid': pid,
            'event_type': event_type,
            'message': message_content
        }
    return None

def parse_modsecurity_message(message):
    modsecurity_pattern = re.compile(
        r'<(?P<priority>\d+)>(?P<timestamp>\S+ \d+ \d+:\d+:\d+) (?P<hostname>\S+) modsecurity\[(?P<pid>\d+)\]: '
        r'(?P<transaction_id>\S+): (?P<rule_id>\d+): (?P<severity>\d+): (?P<message>.+)'
    )
    match = modsecurity_pattern.match(message)
    if match:
        priority = int(match.group('priority'))
        facility = priority // 8
        severity = priority % 8
        timestamp = match.group('timestamp')
        hostname = match.group('hostname')
        pid = match.group('pid')
        transaction_id = match.group('transaction_id')
        rule_id = match.group('rule_id')
        severity_level = match.group('severity')
        message_content = match.group('message')
        return {
            'type': 'modsecurity',
            'facility': facility,
            'severity': severity,
            'timestamp': timestamp,
            'hostname': hostname,
            'pid': pid,
            'transaction_id': transaction_id,
            'rule_id': rule_id,
            'severity_level': severity_level,
            'message': message_content
        }
    return None

def parse_syslog_message(message):
    parsed_message = parse_ossec_message(message)
    if parsed_message is None:
        parsed_message = parse_suricata_message(message)
    if parsed_message is None:
        parsed_message = parse_modsecurity_message(message)
    if parsed_message is None:
        logging.error(f"Failed to parse message: {message}")
    return parsed_message

def handle_message(message_queue):
    while True:
        message = message_queue.get()
        if message is None:
            break
        parsed_message = parse_syslog_message(message)
        if parsed_message:
            if parsed_message['type'] == 'ossec':
                logging.info(
                    f"OSSEC - Facility: {parsed_message['facility']}, Severity: {parsed_message['severity']}, "
                    f"Timestamp: {parsed_message['timestamp']}, Hostname: {parsed_message['hostname']}, "
                    f"Process: {parsed_message['process']}, PID: {parsed_message['pid']}, Rule ID: {parsed_message['rule_id']}, "
                    f"Level: {parsed_message['level']}, Description: {parsed_message['description']}, Message: {parsed_message['message']}"
                )
            elif parsed_message['type'] == 'suricata':
                logging.info(
                    f"Suricata - Facility: {parsed_message['facility']}, Severity: {parsed_message['severity']}, "
                    f"Timestamp: {parsed_message['timestamp']}, Hostname: {parsed_message['hostname']}, "
                    f"PID: {parsed_message['pid']}, Event Type: {parsed_message['event_type']}, Message: {parsed_message['message']}"
                )
            elif parsed_message['type'] == 'modsecurity':
                logging.info(
                    f"ModSecurity - Facility: {parsed_message['facility']}, Severity: {parsed_message['severity']}, "
                    f"Timestamp: {parsed_message['timestamp']}, Hostname: {parsed_message['hostname']}, "
                    f"PID: {parsed_message['pid']}, Transaction ID: {parsed_message['transaction_id']}, "
                    f"Rule ID: {parsed_message['rule_id']}, Severity Level: {parsed_message['severity_level']}, Message: {parsed_message['message']}"
                )
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
                data, addr = sock.recvfrom(1024)  # Buffer size is 1024 bytes
                message = data.decode('utf-8')
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