FORMAT: 1A
HOST: https://auth-stage.copyrighthub.org

# Open Permissions Platform Auth Service

The service provides endpoints for generating OAuth 2 tokens and for verifying
a token bearer's access to a protected resource, such as a service or repository.

## Authorization

This API requires HTTP Basic authentication, with the service's client ID and secret as the username and password. 
These are available via the accounts service API and UI).

## Standard error output
On endpoint failure there is a standard way to report errors.
The output should be of the form

| Property | Description               | Type   |
| :------- | :----------               | :---   |
| status   | The status of the request | number |
| errors   | A list of errors          | list   |

### Error
| Property | Description                                 | Type   |
| :------- | :----------                                 | :---   |
| source   | The name of the service producing the error | number |
| message  | A description of the error                  | string |

# Group Authentication

## Authentication service information [/v1/auth]

### Retrieve service information [GET]

#### Output
| Property | Description               | Type   |
| :------- | :----------               | :---   |
| status   | The status of the request | number |
| data     | The service information   | object |

##### Service information
| Property     | Description                    | Type   |
| :-------     | :----------                    | :---   |
| service_name | The name of the api service    | string |
| version      | The version of the api service | string |


+ Request service information
    + Headers

            Accept: application/json

+ Response 200 (application/json; charset=UTF-8)
    + Body

            {
                "status": 200,
                "data": {
                    "service_name": "Open Permissions Platform Authentication Service",
                    "version": "0.1.0"
                }
            }

## Request an authorization token [/v1/auth/token]

#### Authorization Grants

Two OAuth authorization grants are supported:

- Client credentials grant ([RFC6749](https://tools.ietf.org/html/rfc6749#section-4.4)): request an access token using the client's credentials
- JSON web token grant ([RFC7523](https://tools.ietf.org/html/rfc7523)): request an access token, authorized by a JWT from another client (used for delegated access)

#### Token Scope

A token scope is a space separated list of strings with the form `action[resource_id]`. 
A `resource_id` can be a service or repository ID, and actions can be one of:

- read (`resource_id` may be excluded for a token that can potentially read any resource accessible to the client), e.g. "read" or "read[1234]"
- write (`resource_id` is required), e.g. "write[1234]"
- delegate (`resource_id` must be a service ID), e.g. "delegate[1234]:write[5678]"

When delegating to another service, the delegated action must be included e.g. delegate[1234]:write[5678] delegates service 1234 to write to resource 5678 on the client's behalf. 
The delegate service then exchanges the provided access token for a token to write to the resource using the JSON web token authorization grant.

### Request an authorization token [POST]

#### Input
| Property   | Description                                                       | Type   | Mandatory |
| :--------  | :-------------------------                                        | :----- | :-------- |
| grant_type | client_credentials or urn:ietf:params:oauth:grant-type:jwt-bearer | string | Yes       |
| scope      | The access token's scope, defaults to "read"                      | string | No        |
| assertion  | A JWT, required for JWT grant                                     | string | No        |

#### Output
| Property     | Description                 | Type   |
| :-------     | :----------                 | :---   |
| status       | The status of the request   | number |
| access_token | a RSA signed JSON web token | string |


+ Request a token using client_credentials (application/x-www-form-urlencode)
    + Headers

            Authorization: Basic [client_id:client_secret]
            Accept: application/json

    + Body

            grant_type=client_credentials&scope=write[1234]

+ Response 200 (application/json; charset=UTF-8)
    + Body

            {
                "status": 200,
                "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnQiOnsic2VydmljZV90eXBlIjoiaW5kZXgiLCJvcmdhbmlzYXRpb25faWQiOiJ0ZXN0Y28iLCJpZCI6IjQyMjVmNDc3NGQ2ODc0YTY4NTY1YTA0MTMwMDAxMTQ0In0sImRlbGVnYXRlIjpmYWxzZSwiYXVkIjoibG9jYWxob3N0OjgwMDcvYXV0aG9yaXplIiwiZXhwIjoxNDU3MDE5MDUwLCJpc3MiOiJsb2NhbGhvc3Q6ODAwNy90b2tlbiIsInNjb3BlIjoicmVhZCIsImdyYW50X3R5cGUiOiJjbGllbnRfY3JlZGVudGlhbHMiLCJzdWIiOiI0MjI1ZjQ3NzRkNjg3NGE2ODU2NWEwNDEzMDAwMTE0NCJ9.D7A1xns-AU1ARPoUyYSD2jT9d_WtIW6hunEYQnMUr5KZAt9rAlsrLFv1nXjdT7WDKObNWUDX9hrmKmzwQkliBIxNZ2yCo71U9-DpKUNK2PbpdgxLgMDDf0GF2QYm1lC_1i8eGBv0WrsuTtoymaIn9xG1M6OG_AmNlFA-Tc3EG5UKbnJ3pXdSIc9Du_sgSy4K2AwcUfCnQjy1BQBuGbiIcGWb5X0IkhC1rGltFC4tUcx1SNx5OFHlEdcrWaQdsAuHh5Ry8sKkCLH0969cThYH_CDjkhwJMWn8F2uwYWkNZLI0vdFaGJgXKfWxM5ro3hzUV763fucEzSM6XgUOOQwhyg"
            }


+ Request convert a delegate token using JWT bearer grant (application/x-www-form-urlencode)
    + Headers

            Authorization: Basic [client_id:client_secret]
            Accept: application/json

    + Body

            grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&scope=write[1234]&assertion=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnQiOnsic2VydmljZV90eXBlIjoiaW5kZXgiLCJvcmdhbmlzYXRpb25faWQiOiJ0ZXN0Y28iLCJpZCI6IjQyMjVmNDc3NGQ2ODc0YTY4NTY1YTA0MTMwMDAxMTQ0In0sImRlbGVnYXRlIjpmYWxzZSwiYXVkIjoibG9jYWxob3N0OjgwMDcvYXV0aG9yaXplIiwiZXhwIjoxNDU3MDE5MDUwLCJpc3MiOiJsb2NhbGhvc3Q6ODAwNy90b2tlbiIsInNjb3BlIjoicmVhZCIsImdyYW50X3R5cGUiOiJjbGllbnRfY3JlZGVudGlhbHMiLCJzdWIiOiI0MjI1ZjQ3NzRkNjg3NGE2ODU2NWEwNDEzMDAwMTE0NCJ9.D7A1xns-AU1ARPoUyYSD2jT9d_WtIW6hunEYQnMUr5KZAt9rAlsrLFv1nXjdT7WDKObNWUDX9hrmKmzwQkliBIxNZ2yCo71U9-DpKUNK2PbpdgxLgMDDf0GF2QYm1lC_1i8eGBv0WrsuTtoymaIn9xG1M6OG_AmNlFA-Tc3EG5UKbnJ3pXdSIc9Du_sgSy4K2AwcUfCnQjy1BQBuGbiIcGWb5X0IkhC1rGltFC4tUcx1SNx5OFHlEdcrWaQdsAuHh5Ry8sKkCLH0969cThYH_CDjkhwJMWn8F2uwYWkNZLI0vdFaGJgXKfWxM5ro3hzUV763fucEzSM6XgUOOQwhyg

+ Response 200 (application/json; charset=UTF-8)
    + Body

            {
                "status": 200,
                "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnQiOnsic2VydmljZV90eXBlIjoiaW5kZXgiLCJvcmdhbmlzYXRpb25faWQiOiJ0ZXN0Y28iLCJpZCI6IjQyMjVmNDc3NGQ2ODc0YTY4NTY1YTA0MTMwMDAxMTQ0In0sImRlbGVnYXRlIjpmYWxzZSwiYXVkIjoibG9jYWxob3N0OjgwMDcvYXV0aG9yaXplIiwiZXhwIjoxNDU3MDE5MDUwLCJpc3MiOiJsb2NhbGhvc3Q6ODAwNy90b2tlbiIsInNjb3BlIjoicmVhZCIsImdyYW50X3R5cGUiOiJjbGllbnRfY3JlZGVudGlhbHMiLCJzdWIiOiI0MjI1ZjQ3NzRkNjg3NGE2ODU2NWEwNDEzMDAwMTE0NCJ9.D7A1xns-AU1ARPoUyYSD2jT9d_WtIW6hunEYQnMUr5KZAt9rAlsrLFv1nXjdT7WDKObNWUDX9hrmKmzwQkliBIxNZ2yCo71U9-DpKUNK2PbpdgxLgMDDf0GF2QYm1lC_1i8eGBv0WrsuTtoymaIn9xG1M6OG_AmNlFA-Tc3EG5UKbnJ3pXdSIc9Du_sgSy4K2AwcUfCnQjy1BQBuGbiIcGWb5X0IkhC1rGltFC4tUcx1SNx5OFHlEdcrWaQdsAuHh5Ry8sKkCLH0969cThYH_CDjkhwJMWn8F2uwYWkNZLI0vdFaGJgXKfWxM5ro3hzUV763fucEzSM6XgUOOQwhyg"
            }


+ Request Unauthorized for the requested scope (application/x-www-form-urlencode)
    + Headers

            Authorization: Basic [client_id:client_secret]
            Accept: application/json

    + Body

            grant_type=client_credentials&scope=write[4225f4774d6874a68565a04130001144]

+ Response 403 (application/json; charset=UTF-8)
    + Body

            {
                "errors": [
                    {
                        "message": "Client 'b0566e4cbfda2ff857f6014a7c0312ee' does not have 'w' access to '4225f4774d6874a68565a04130001144'",
                        "source": "authentication"
                    }
                ],
                "status": 403
            }

## Verify token authorization [/v1/auth/verify]

### Verify a token is authorized [POST]

Verify that a token bearer is authorized to access a resource.

#### Input
| Property         | Description                                   | Type   | Mandatory |
| :--------        | :-------------------------                    | :----- | :-------- |
| token            | An access token                               | string | Yes       |
| requested_access | Type of access (r/w/rw) requested             | string | Yes       |
| resource_id      | ID of a hosted resource, e.g. a repository ID | string | No        |

#### Output
| Property   | Description                                            | Type    |
| :-------   | :----------                                            | :---    |
| status     | The status of the request                              | number  |
| has_access | Whether the token is authorized to access the resource | boolean |

+ Request Token is authorized to read service (application/x-www-form-urlencode)
    + Headers

            Authorization: Basic [client_id:client_secret]
            Accept: application/json

    + Body

            requested_access=r&token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnQiOnsic2VydmljZV90eXBlIjoiaW5kZXgiLCJvcmdhbmlzYXRpb25faWQiOiJ0ZXN0Y28iLCJpZCI6IjQyMjVmNDc3NGQ2ODc0YTY4NTY1YTA0MTMwMDAxMTQ0In0sImRlbGVnYXRlIjpmYWxzZSwiYXVkIjoibG9jYWxob3N0OjgwMDcvYXV0aG9yaXplIiwiZXhwIjoxNDU3MDE5MDUwLCJpc3MiOiJsb2NhbGhvc3Q6ODAwNy90b2tlbiIsInNjb3BlIjoicmVhZCIsImdyYW50X3R5cGUiOiJjbGllbnRfY3JlZGVudGlhbHMiLCJzdWIiOiI0MjI1ZjQ3NzRkNjg3NGE2ODU2NWEwNDEzMDAwMTE0NCJ9.D7A1xns-AU1ARPoUyYSD2jT9d_WtIW6hunEYQnMUr5KZAt9rAlsrLFv1nXjdT7WDKObNWUDX9hrmKmzwQkliBIxNZ2yCo71U9-DpKUNK2PbpdgxLgMDDf0GF2QYm1lC_1i8eGBv0WrsuTtoymaIn9xG1M6OG_AmNlFA-Tc3EG5UKbnJ3pXdSIc9Du_sgSy4K2AwcUfCnQjy1BQBuGbiIcGWb5X0IkhC1rGltFC4tUcx1SNx5OFHlEdcrWaQdsAuHh5Ry8sKkCLH0969cThYH_CDjkhwJMWn8F2uwYWkNZLI0vdFaGJgXKfWxM5ro3hzUV763fucEzSM6XgUOOQwhyg


+ Response 200 (application/json; charset=UTF-8)
    + Body

            {
                "status": 200,
                "has_access": true
            }


+ Request Token is not authorized to write to service (application/x-www-form-urlencode)
    + Headers

            Authorization: Basic [client_id:client_secret]
            Accept: application/json

    + Body

            requested_access=r&token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnQiOnsic2VydmljZV90eXBlIjoiaW5kZXgiLCJvcmdhbmlzYXRpb25faWQiOiJ0ZXN0Y28iLCJpZCI6IjQyMjVmNDc3NGQ2ODc0YTY4NTY1YTA0MTMwMDAxMTQ0In0sImRlbGVnYXRlIjpmYWxzZSwiYXVkIjoibG9jYWxob3N0OjgwMDcvYXV0aG9yaXplIiwiZXhwIjoxNDU3MDE5MDUwLCJpc3MiOiJsb2NhbGhvc3Q6ODAwNy90b2tlbiIsInNjb3BlIjoicmVhZCIsImdyYW50X3R5cGUiOiJjbGllbnRfY3JlZGVudGlhbHMiLCJzdWIiOiI0MjI1ZjQ3NzRkNjg3NGE2ODU2NWEwNDEzMDAwMTE0NCJ9.D7A1xns-AU1ARPoUyYSD2jT9d_WtIW6hunEYQnMUr5KZAt9rAlsrLFv1nXjdT7WDKObNWUDX9hrmKmzwQkliBIxNZ2yCo71U9-DpKUNK2PbpdgxLgMDDf0GF2QYm1lC_1i8eGBv0WrsuTtoymaIn9xG1M6OG_AmNlFA-Tc3EG5UKbnJ3pXdSIc9Du_sgSy4K2AwcUfCnQjy1BQBuGbiIcGWb5X0IkhC1rGltFC4tUcx1SNx5OFHlEdcrWaQdsAuHh5Ry8sKkCLH0969cThYH_CDjkhwJMWn8F2uwYWkNZLI0vdFaGJgXKfWxM5ro3hzUV763fucEzSM6XgUOOQwhyg


+ Response 200 (application/json; charset=UTF-8)
    + Body

            {
                "status": 200,
                "has_access": false
            }

+ Request Token is authorized to read repository (application/x-www-form-urlencode)
    + Headers

            Authorization: Basic [client_id:client_secret]
            Accept: application/json

    + Body

            resource_id=b0566e4cbfda2ff857f6014a7c00807a&requested_access=r&token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnQiOnsic2VydmljZV90eXBlIjoiaW5kZXgiLCJvcmdhbmlzYXRpb25faWQiOiJ0ZXN0Y28iLCJpZCI6IjQyMjVmNDc3NGQ2ODc0YTY4NTY1YTA0MTMwMDAxMTQ0In0sImRlbGVnYXRlIjpmYWxzZSwiYXVkIjoibG9jYWxob3N0OjgwMDcvYXV0aG9yaXplIiwiZXhwIjoxNDU3MDE5MDUwLCJpc3MiOiJsb2NhbGhvc3Q6ODAwNy90b2tlbiIsInNjb3BlIjoicmVhZCIsImdyYW50X3R5cGUiOiJjbGllbnRfY3JlZGVudGlhbHMiLCJzdWIiOiI0MjI1ZjQ3NzRkNjg3NGE2ODU2NWEwNDEzMDAwMTE0NCJ9.D7A1xns-AU1ARPoUyYSD2jT9d_WtIW6hunEYQnMUr5KZAt9rAlsrLFv1nXjdT7WDKObNWUDX9hrmKmzwQkliBIxNZ2yCo71U9-DpKUNK2PbpdgxLgMDDf0GF2QYm1lC_1i8eGBv0WrsuTtoymaIn9xG1M6OG_AmNlFA-Tc3EG5UKbnJ3pXdSIc9Du_sgSy4K2AwcUfCnQjy1BQBuGbiIcGWb5X0IkhC1rGltFC4tUcx1SNx5OFHlEdcrWaQdsAuHh5Ry8sKkCLH0969cThYH_CDjkhwJMWn8F2uwYWkNZLI0vdFaGJgXKfWxM5ro3hzUV763fucEzSM6XgUOOQwhyg


+ Response 200 (application/json; charset=UTF-8)
    + Body

            {
                "status": 200,
                "has_access": true
            }


+ Request Token is not authorized to write to repository (application/x-www-form-urlencode)
    + Headers

            Authorization: Basic [client_id:client_secret]
            Accept: application/json

    + Body

            resource_id=b0566e4cbfda2ff857f6014a7c00807a&requested_access=r&token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnQiOnsic2VydmljZV90eXBlIjoiaW5kZXgiLCJvcmdhbmlzYXRpb25faWQiOiJ0ZXN0Y28iLCJpZCI6IjQyMjVmNDc3NGQ2ODc0YTY4NTY1YTA0MTMwMDAxMTQ0In0sImRlbGVnYXRlIjpmYWxzZSwiYXVkIjoibG9jYWxob3N0OjgwMDcvYXV0aG9yaXplIiwiZXhwIjoxNDU3MDE5MDUwLCJpc3MiOiJsb2NhbGhvc3Q6ODAwNy90b2tlbiIsInNjb3BlIjoicmVhZCIsImdyYW50X3R5cGUiOiJjbGllbnRfY3JlZGVudGlhbHMiLCJzdWIiOiI0MjI1ZjQ3NzRkNjg3NGE2ODU2NWEwNDEzMDAwMTE0NCJ9.D7A1xns-AU1ARPoUyYSD2jT9d_WtIW6hunEYQnMUr5KZAt9rAlsrLFv1nXjdT7WDKObNWUDX9hrmKmzwQkliBIxNZ2yCo71U9-DpKUNK2PbpdgxLgMDDf0GF2QYm1lC_1i8eGBv0WrsuTtoymaIn9xG1M6OG_AmNlFA-Tc3EG5UKbnJ3pXdSIc9Du_sgSy4K2AwcUfCnQjy1BQBuGbiIcGWb5X0IkhC1rGltFC4tUcx1SNx5OFHlEdcrWaQdsAuHh5Ry8sKkCLH0969cThYH_CDjkhwJMWn8F2uwYWkNZLI0vdFaGJgXKfWxM5ro3hzUV763fucEzSM6XgUOOQwhyg


+ Response 200 (application/json; charset=UTF-8)
    + Body

            {
                "status": 200,
                "has_access": false
            }
