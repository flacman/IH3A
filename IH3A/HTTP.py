import requests
import json

class SourceAddressAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, source_address, *args, **kwargs):
        self.source_address = source_address
        super(SourceAddressAdapter, self).__init__(*args, **kwargs)

    def get_connection(self, url, proxies=None):
        conn = super(SourceAddressAdapter, self).get_connection(url, proxies)
        conn.source_address = (self.source_address, 0)
        return conn

class HTTPQuery:
    def __init__(self, host, path="", use_post=True, use_json=False, default_headers=None):
        self.host = host
        self.path = path
        self.use_post = use_post
        self.use_json = use_json
        self.default_headers = default_headers if default_headers else {}
        
        self.ip_counter = 0

    def build_post_query(self, username, password):
        if self.use_json:
            return json.dumps({"username": username, "password": password})
        else:
            return f"username={username}&password={password}"

    def perform_query(self, username="", password="", search_string="", ip="0.0.0.0", changeIP=False):
        # Merge default headers with provided headers
        final_headers = self.default_headers.copy()

        # Build the post query
        post_query = self.build_post_query(username, password)

        # Construct the full URL
        url = self.host
        if self.path:
            url = f"{self.host.rstrip('/')}/{self.path.lstrip('/')}"

        # Determine the data to send based on use_json
        if self.use_json:
            data = post_query
            final_headers['Content-Type'] = 'application/json'
        else:
            data = post_query
            final_headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        # Perform the HTTP request using a session to handle cookies
        session = requests.Session()



        session.mount('http://', SourceAddressAdapter(ip))
        if self.use_post:
            if self.use_json:
                response = session.post(url, headers=final_headers, json=json.loads(data), allow_redirects=True)
            else:
                response = session.post(url, headers=final_headers, data=data, allow_redirects=True)
        else:
            response = session.get(url, headers=final_headers, params=data, allow_redirects=True)

        # Check if the search string is in the response content
        if search_string in response.text:
            return True

        # Check if an access token is set in the JSON response
        try:
            response_json = response.json()
            if 'access_token' in response_json:
                return True, response.status_code, response.text
        except ValueError:
            pass
        return False, response.status_code, response.text
if __name__ == "__main__":
    # Example usage:
    http_query = HTTPQuery(
        host="http://192.168.16.146:8081",
        default_headers={"Content-Type": "application/x-www-form-urlencoded"},
        post_query="username=${USER}&password=${PASS}",
        path="/login",
        use_post=True,
        use_json=False
    )
    ip = '192.168.16.1'

    result = http_query.perform_query(username="myuser", password="mypassword", search_string="Welcome", ip=ip)
    ip = '192.168.16.3'
    result = http_query.perform_query(username="myuser", password="mypassword", search_string="Welcome", ip=ip)
    print(result)  # True if "Welcome" is in the response or if an access token is set, False otherwise