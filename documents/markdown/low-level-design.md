# Auth Service Design

## Overview

Clients are required to authenticate themselves with the auth service to get a
token that authorises limited access to resources (services or repositories)
within the hub.

The auth service implements [OAuth 2](https://tools.ietf.org/html/rfc6749) for
authorising access to protected resources using either the
[client credentials grant](https://tools.ietf.org/html/rfc6749#section-4.4) or
the [JWT grant](https://tools.ietf.org/html/rfc7523#section-2.1).

## Token Scope

All tokens include a [scope](https://tools.ietf.org/html/rfc6749#section-3.3)
limiting the token's access. Scopes are a space separated list of strings, and
must contain at least one of these actions:

- __read__: token bearer may read from resources
- __write__:  the token bearer my write to a resource
- __delegate__: the token recipient may exchange the token for a read or write
  token to act on the token bearer's behalf

A resource is specified within the scope by including it's ID or registered URL
(for services only) within square brackets. In case a token is compromised, any
damage will be limited to the specifid resources. For example

```
write[1234] read[http://test.com]
```

grants write access to a resource with ID `1234` and read access to a service
registered with `http://test.com`. The client may opt to not include a resource
ID when reading (i.e. the scope is just `read`) to obtain a token that may be
used to read from any resource (it's assumed that the resource will verify
access).

The read scope allows a broader scope because the risk from a compromised token
is smaller, and a broader read scope is beneficial for services that need to
read from many resources (e.g. the query service).

When requesting a "delegate" scope, the delegated action (either read or write)
must be included, separated with a colon. For example

```
delegate[1234]:write[5678]
```

authorises service `1234` to write to resource `5678` on the client's behalf.
The first resource must be a service, while the second may be another service
or a repository. A delegate scope authorises the recipient to request a token
from the auth service to access a resource on the client's behalf, but the
delegate scope does not authorise the token bearer to access the resource
directly.

In the previous example, service `1234` would not be able write to `5678`
without first requesting a token using the JWT grant (described below).

## Requesting a token

### Client credentials grant

See [RFC6749](https://tools.ietf.org/html/rfc6749#section-4.4)

In most cases a client will use the client credentials grant. The client will
need to authenticate using HTTP Basic authentication, using their client ID and
secret as the username and password (the client ID and secret are retrievable
from the accounts user interface). The client's credentials must be included in
the `Authorization` header, and may not be included in the request body or URI.
The `grant_type` parameter must be `client_credentials`, and the `scope` may be
included (tokens default to "read" scope if not provided).

If the client is authorised, the auth service responds with a JSON response
containing a [JSON Web Token (JWT)](https://tools.ietf.org/html/rfc7519) bearer
access token:

```json
{
    "access_token": "aaa.bbb.ccc",
    "token_type": "bearer",
    "expiry": 1457365331,
    "status": 200
}
```

The `expiry` is a UTC timestamp (seconds since the epoch), once the token has
expired it can no longer be used.

### JWT grant

See [RFC7523](https://tools.ietf.org/html/rfc7523#section-2.1)

In cases where a client has received a JWT containing a "delegate" scope, the
client may promote the JWT to authorise delegated access. For example, the
client may use a token containing scope `delegate[1234]:write[5678]` to request
a token with the scope `write[5678]`.

The client will need to authenticate using HTTP Basic authentication, using
their client ID and secret as the username and password (the client ID and
secret are retrievable from the accounts service). The client's credentials
must be included in the `Authorization` header, and may not be included in the
request body or URI. The client ID must be associated with the service ID or
URL included in the JWT's scope. For example, if the JWT contains
`delegate[1234]:write[5678]`, then the client must have ID `1234`.

The request must include the following parameters:

- the `grant_type` parameter must be
  `urn:ietf:params:oauth:grant-type:jwt-bearer`
- the `assertion` parameter must be the JWT authorising the client's access
- the `scope` must match a delegated scope within the JWT (e.g. `write[5678]`
  if the JWT contains `delegate[1234]:write[5678]`)

If the client is authorised, the auth service responds with a JSON response
containing another [JSON Web Token (JWT)](https://tools.ietf.org/html/rfc7519)
access token:

```json
{
    "access_token": "aaa.bbb.ccc",
    "token_type": "bearer",
    "expiry": 1457365331,
    "status": 200
}
```

The `expiry` is a UTC timestamp (seconds since the epoch), once the token has
expired it can no longer be used.


## Accessing a protected resource

When accessing a resource, the access token should be included in the
`Authorization` header, preceded by "Bearer", e.g. `Bearer aaa.bb.ccc`.

### Access verification

The service that receives the token verifies the token with the auth service
before modifying or serving any data. The service will need to authenticate
using HTTP Basic authentication using their client ID and secret. The request
should contain:

- the `token` parameter should be the access token
- the `requested_access` token should be the type of access requested (e.g. a
  `GET` request is usually `r` and a `POST` is usually `w`)
- if the resource is a repository, then the repository's ID should be included
  as the `resource_id`. The `resource_id` is not required for services as they
  are identified by the client ID.

The auth service will respond with a JSON response containing `has_access`,
which will be `true` if the token is authorised to access the resource and
`false` otherwise:

```json
{
    "status": 200,
    "has_access": true
}
```

If the token is not authorised, the service must respond to the client with a
403 error code.

### Repositories

If the requested resource is a repository, the client must be authorised to
access the repository service as well as the repository. Similarly, for
delegated access the client _and_ delegate must have access to the repository
service (but only the client needs to have access to the repository). It is
expected that most repository services will not restrict access to the service,
instead leaving access control up to the repositories hosted by the service.

## JSON Web Tokens (JWT)

JWT's have a [standard set of claims](https://tools.ietf.org/html/rfc7519#section-4.1)
that may be included and can be extended with application-specific claims.

The JWTs issued by the auth service contain:

- `exp`: the token expiry date/time, represented by a UTC timestamp in seconds
  since the epoch
- `iss`: the token issuer (the auth service) URI
- `aud`: the token's audience (the auth service's verify endpoint)
- `sub`: the subject, either the client or the delegate `client_id`
- `client`: a JSON object containing the client `id`, `service_type` &
  `organisation_id`. If access has been delegated, this will contain the
  original client not the delegate
- `scope`: the token's scope
- `grant_type`: the token's grant type (`client_credentials` or
  `urn:ietf:params:oauth:grant-type:jwt-bearer`)
- `delegate`: `true` if the token has been issued to a delegate, otherwise
  `false`

The JWT is signed by the auth service using the RSASSA-PKCS1-v1_5 signature
algorithm using the SHA-256 hash algorithm, and can be verified with the
service's SSL public key.


## Sequence Diagrams

### Querying

![](./images/auth-query-example.png)

### Onboarding

![](./images/auth-onboarding-example.png)
