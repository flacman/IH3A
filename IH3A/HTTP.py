import requests
import json

class HTTPQuery:
    def __init__(self, host, default_headers=None, post_query="", path="", use_post=True, use_json=False):
        self.host = host
        self.default_headers = default_headers if default_headers else {}
        self.post_query = post_query
        self.path = path
        self.use_post = use_post
        self.use_json = use_json

    def build_post_query(self, username, password):
        if self.use_json:
            return json.dumps({"username": username, "password": password})
        else:
            return f"username={username}&password={password}"
    
    #for the model, output whether or not we were able to login (success), the http status code and response text
    def perform_query_verbose(self, username="", password="", search_string=""):
        # Merge default headers with provided headers
        final_headers = self.default_headers.copy()

        # Build the post query
        post_query = self.build_post_query(username, password)

        # Construct the full URL
        url = self.host
        if self.path:
            url = f"{self.host.rstrip('/')}/{self.path.lstrip('/')}"

        data = post_query
        # Determine the data to send based on use_json
        if self.use_json:
            final_headers['Content-Type'] = 'application/json'
#        else:
#            final_headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        # Perform the HTTP request using a session to handle cookies
        session = requests.Session()
        if self.use_post:
            if self.use_json:
                response = session.post(url, headers=final_headers, json=json.loads(data), allow_redirects=True)
            else:
                response = session.post(url, headers=final_headers, data=data, allow_redirects=True)
                    
        else:
            response = session.get(url, headers=final_headers, params=data, allow_redirects=True)

        # status_code = response.status_code
        # status_code = response.status_code
        if search_string in response.text:
            return True, response.status_code, response.text
        try:
            response_json = response.json()
            if 'access_token' in response_json:
                return True, response.status_code, response.text
        except ValueError:
            pass
        return False, response.status_code, response.text


    def perform_query(self, username="", password="", search_string=""):
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
        
        # Perform the HTTP request using a session to handle cookies
        session = requests.Session()
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
                return True
        except ValueError:
            pass

        return False

# Example usage:
# http_query = HTTPQuery(
#     host="http://example.com",
#     default_headers={"Content-Type": "application/x-www-form-urlencoded"},
#     post_query="username=${USER}&password=${PASS}",
#     path="/login",
#     use_post=True,
#     use_json=False
# )
# result = http_query.perform_query(username="myuser", password="mypassword", search_string="Welcome")
# print(result)  # True if "Welcome" is in the response or if an access token is set, False otherwise