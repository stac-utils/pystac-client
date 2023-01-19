# Authentication

While not integrated into this library directly, pystac-client provides a series of hooks that support a wide variety of authentication mechanisms. These can be used when interacting with stac API implementations behind various authorization walls.

## Basic auth

Pystac-client supports HTTP basic authentication by simply exposing the ability to define headers to be used when sending requests.  Simply encode the token and provide the header.

```python
import base64
import pystac_client

# encode credentials
user_name = "yellowbeard"
password = "yaarg"
userpass = f"{user_name}:{password}"
b64_userpass = base64.b64encode(userpass.encode()).decode()

# create the client
client = pystac_client.Client.open(
    url="https://planetarycomputer.microsoft.com/api/stac/v1",
    headers={
        'Authorization': f"Basic {b64_userpass}"
    }
)
```

## Token auth

Providing a authentication token can be accomplished using the same mechanism as described above for [basic auth](#basic-auth). Simply provide the token in the `Authorization` header to the client in the same manner.

## AWS SigV4

Accessing a stac api protected by AWS IAM often requires signing the request using [AWS SigV4](https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html). Unlike basic and token authentication, the entire request is part of the signing process. Thus the `Authorization` header cannot be added when the client is created, rather it must be generated and added after the request is fully formed.

Pystac-client provides a lower-level hook, the `request_modifier` parameter, which can mutate the request, adding the necessary header after the request has been generated but before it is sent.

The code cell below demonstrates this, using the `boto3` module.

```python
import boto3
import botocore.auth
import botocore.awsrequest
import pystac_client
import requests

# Details regarding the private stac api
region = "us-east-1"
service_name = "execute-api"
endpoint_id = "xxxxxxxx"
deployment_stage = "dev"
stac_api_url = f"https://{endpoint_id}.{service_name}.{region}.amazonaws.com/{deployment_stage}"

# load AWS credentials
credentials = boto3.Session(region_name=region).get_credentials()
signer = botocore.auth.SigV4Auth(credentials, service_name, region)

def sign_request(request: requests.Request) -> requests.Request:
    """Sign the request using AWS SigV4.

    Args:
        request (requests.Request): The fully populated request to sign.

    Returns:
        requests.Request: The provided request object, with auth header added.
    """
    aws_request = botocore.awsrequest.AWSRequest(
        method=request.method,
        url=request.url,
        params=request.params,
        data=request.data,
        headers=request.headers
    )
    signer.add_auth(aws_request)
    request.headers = aws_request.headers
    return request

# create the client
client = pystac_client.Client.open(
    url=stac_api_url,
    request_modifier=sign_request
)
```
