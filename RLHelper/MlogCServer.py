from flask import Flask, request, jsonify, abort
import re
from datetime import datetime
from dateutil.parser import parse as parse_date
from SharedMemLib import Mode, read_write_sharedMem  # Import the function to write to shared memory

app = Flask(__name__)

def parse_log(log):
    # Regex pattern with named groups for better clarity
    pattern = (
        r'^\[(?P<facility>[^.]+)\.(?P<severity>[^\]]+)\]\s*'
        r'\[(?P<timestamp>[^\]]+)\]\s*'
        r'\[(?P<hostname>[^\]]*)\]\s*'
        r'\[(?P<pid>[^\]]*)\]\s*'
        r'\[(?P<transaction_id>[^\]]*)\]\s*'
        r'\[(?P<rule_id>[^\]]*)\]\s*'
        r'\[(?P<severity_level>[^\]]*)\]\s*'
        r'(?:\[.*?\]\s*)*'  # Non-capturing group to skip any additional brackets
        r'(?P<message>.*)'
    )

    match = re.match(pattern, log.strip(), re.DOTALL)
    if not match:
        return None  # Invalid log format

    try:
        facility = match.group('facility')
        severity = match.group('severity')
        timestamp_str = match.group('timestamp')
        hostname = match.group('hostname')
        pid = match.group('pid')
        transaction_id = match.group('transaction_id')
        rule_id = match.group('rule_id')
        severity_level = match.group('severity_level')
        message_content = match.group('message').strip()

        # Parse timestamp using dateutil for flexibility
        try:
            timestamp = parse_date(timestamp_str)
        except ValueError:
            return None  # Invalid timestamp format

        # Validate and convert PID to integer if possible
        pid = pid.strip()
        if pid.isdigit():
            pid = int(pid)
        else:
            pid = None  # PID is not a valid number

        # Convert severity_level to integer if possible
        severity_level = severity_level.strip()
        if severity_level.isdigit():
            severity_level = int(severity_level)
        else:
            severity_level = None  # Severity level is not a valid number

        return {
            'type': 'modsecurity',
            'facility': facility.strip(),
            'severity': severity.strip(),
            'timestamp': timestamp.isoformat(),
            'hostname': hostname.strip(),
            'pid': pid,
            'transaction_id': transaction_id.strip(),
            'rule_id': rule_id.strip(),
            'severity_level': severity_level,
            'message': message_content
        }
    except Exception:
        # Handle any unexpected exceptions
        return None  # Parsing failed due to an unexpected error

@app.route('/logs', methods=['POST'])
def receive_log():
    if not request.data:
        abort(400, description="No data provided")
    try:
        log = request.data.decode('utf-8')
        parsed_log = parse_log(log)

        if not parsed_log:
            abort(400, description="Invalid log format")
        str_to_write = (
            f"ModSecurity - Facility: {parsed_log['facility']}, "
            f"Severity: {parsed_log['severity']}, "
            f"Timestamp: {parsed_log['timestamp']}, "
            f"Hostname: {parsed_log['hostname']}, "
            f"PID: {parsed_log['pid']}, "
            f"Transaction ID: {parsed_log['transaction_id']}, "
            f"Rule ID: {parsed_log['rule_id']}, "
            f"Severity Level: {parsed_log['severity_level']}, "
            f"Message: {parsed_log['message']}"
        )
        # Write the parsed log to shared memory
        read_write_sharedMem(Mode.Write, str_to_write)

        return jsonify(parsed_log), 200
    except Exception as e:
        abort(400, description="Error processing log")

if __name__ == '__main__':
    # Set debug to False in production
    app.run(host='0.0.0.0', port=5000, debug=False)