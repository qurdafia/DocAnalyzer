import requests

class RequestsProvider:
    """
    A generic wrapper for the requests library to ensure consistent settings,
    like SSL verification.
    """
    def __init__(self, verify=True):
        """
        Initializes the provider.
        Args:
            verify (bool or str): Path to a CA bundle or boolean to enable/disable SSL verification.
        """
        self.verify = verify

    def post(self, url, **kwargs):
        return requests.post(url, verify=self.verify, **kwargs)

    def get(self, url, **kwargs):
        return requests.get(url, verify=self.verify, **kwargs)