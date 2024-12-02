import requests
from ftplib import FTP, error_perm, error_temp, all_errors

class SourceAddressAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, source_address, *args, **kwargs):
        self.source_address = source_address
        super(SourceAddressAdapter, self).__init__(*args, **kwargs)

    def get_connection(self, url, proxies=None):
        conn = super(SourceAddressAdapter, self).get_connection(url, proxies)
        conn.source_address = (self.source_address, 0)
        return conn

class FTPQuery:
    def __init__(self, host, path=""):
        self.host = host
        self.path = path
        self.ip_counter = 0

    def perform_query(self, username="", password="", search_string="220 ", ip="192.168.16.146", changeIP=False):
        try:
            print(f"Connecting to {self.host} with {username}:{password}")
            ftp = FTP("192.168.16.146")
            ftp.login(user=username, passwd=password)
            welcome_message = ftp.getwelcome()
            print(welcome_message)
            if "530" in welcome_message:
                ftp.quit()
                return False, "User blocked"
            if search_string in welcome_message.lower():
                ftp.quit()
                return True, None
            else:
                ftp.quit()
                return False, "Search string not found"
        except error_perm as e:
            return False, f"Permanent error: {str(e)}"
        except error_temp as e:
            return False, f"Temporary error: {str(e)}"
        except all_errors as e:
            return False, f"FTP error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
if __name__ == "__main__":
    # Example usage:
    ftp_query = FTPQuery(host="192.168.16.147")
    
    result, message = ftp_query.perform_query(username="user", password="password", search_string="220 ")
    print(result)  # True if "Welcome" is in the response or if an access token is set, False otherwise