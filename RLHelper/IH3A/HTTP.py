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

    def perform_query(self, username="", password="", search_string=""):
        # Merge default headers with provided headers
        final_headers = self.default_headers.copy()

        # Replace ${USER} and ${PASS} in the post query
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

        # Perform the HTTP request
        if self.use_post:
            if self.use_json:
                response = requests.post(url, headers=final_headers, json=data)
            else:
                response = requests.post(url, headers=final_headers, data=data)
        else:
            response = requests.get(url, headers=final_headers, params=data)

        # Check if the search string is in the response content
        if search_string in response.text:
            return True
        else:
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
# print(result)  # True if "Welcome" is in the response, False otherwise