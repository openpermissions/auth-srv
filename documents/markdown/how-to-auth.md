<!--
(C) Copyright Open Permissions Platform Coalition 2016
 -->

# How to authenticate with Open Permissions Platform services

## Contents

+ [About this document](#about-this-document)
+ [Overview](#overview)
  + [Services summary](#services-summary)
+ [API status in the current release](#api-status-in-the-current-release)
+ [Usage](#usage)
  + [Client credentials](#client-credentials)
  + [Token scope](#token-scope)
  + [Service and resource IDs](#service-and-resource-ids)
+ [Token request examples](#token-request-examples)
  + [`read` token request and usage](#read-token-request-and-usage)
  + [Delegated `write` token request and usage](#delegated-write-token-request-and-usage)

## About this document

This How-to describes how to authenticate with Open Permissions
Platform services.

For issues and support, contact
[support@openpermissions.org](mailto:support@openpermissions.org)
by email.

### See also

+ The authentication flow follows the [OAuth 2.0 specification](http://tools.ietf.org/html/rfc6749)
+ The client credentials needed to authenticate an application client
  or external service are stored by the Accounts Service, see
  [How to create and manage accounts, services, and users](https://github.com/openpermissions/accounts-srv/blob/master/documents/markdown/how-to-register.md)

## Overview

OPP services, with a few exceptions, accept only authenticated
requests from application clients and collaborating services. The
authentication flow follows OAuth 2.0.

Typically the steps are:

1. Request an OAuth access token with appropriate
   [scope](#token-scope) from the OPP Authentication Service,
   supplying [client credentials](#client-credentials)
2. Supply the token in the API request to the required OPP service

>In practice, since the Query Service accepts unauthenticated
>requests, only those running an external service integrating with OPP
>or developing application clients that use the Onboarding Service
>need to use the authentication flow.

In addition to client credentials, the Authentication Service also
supports the **JWT Bearer** token flow, which is used internally to
exchange a token for delegated access.

For full API details, see the
[Authentication Service API reference](../apiary/api.md).

### Services summary

The table below shows which OPP services expose client application
APIs, and which services require authentication:

+ Services marked __No__ in the __Authenticated__ column are open and
do not require authentication
+ Services marked __Yes__ require authentication as specified

| Service | Client API Yes/No | Authenticated Yes/No |
|---|---|---|
| __Accounts__ | __Yes__ | __No__ |
| __Authentication__ | __Yes__ | __Yes__ Basic Authentication, supply client credentials, returns an OAuth 2.0 access token |
| Identity | No | Yes |
| Index | No | Yes |
| __Onboarding__ | __Yes__ | __Yes__ supply an OAuth 2.0 access token as `Bearer` |
| __Query__ | __Yes__ | __No__ |
| Repository | No | Yes |
| Resolution | No | Yes |
| Template | No | Yes |
| Transformation | No | Yes |

## API status in the current release

+ OAuth 2.0 Client Credentials and JWT Bearer token flows implemented
  by the Authentication Service

### Limitations

+ The Authentication Service expires tokens after a fixed number of
  minutes, sufficient to support bulk actions and normal latencies in
  the system. However, it is recommended that you obtain a new token
  for each API call you make to avoid problems with a token expiring
  before a call completes.

## Usage

Application clients and external services must supply an OAuth access
token as `Bearer` in calls to OPP endpoints that require
authentication.

Tokens are supplied by the Authentication Service.

The Authentication Service uses Basic Authentication with client
credentials to authorise token requests.

### Client credentials

Client credentials are the **client ID** and **secret** that are
assigned to each new service when it is created and stored by the
Accounts Service, and can be found from the Accounts Service web UI,
for details see
[How to create and manage accounts, services, and users](https://github.com/openpermissions/accounts-srv/blob/master/documents/markdown/how-to-register.md).

### Token scope

Tokens include a **scope** which is specified when the token is
requested. A scope is a space separated list of strings consisting of
at least one of:

- `read` &mdash; the token bearer may read from resources
- `write` &mdash; the token bearer may write to a resource
- `delegate` &mdash; the token recipient may exchange the token for a
  read or write token to act on the token bearer's behalf

A `read` scope may be unqualified, but `write` and `delegate` scopes
**must** be qualified with respectively:

- `write` &mdash; the resource ID to be written to, for example a
repository ID `write[<repo_id>]`
- `delegate` &mdash; the service to be delegated to and colon
separated scope to be delegated, for example an Onboarding Service
instance URL or UUID, with `write` scope for a specific repository
`delegate[<service>]:write[<repo_id>]`

If no scope is specified when the token is requested, the token scope
defaults to `read` (unqualified).

In practice, the most common scopes required by an application client are:

+ `read` &mdash; default token allowing read to any resource for which
  the client has read permission, for example a repository belonging
  to the client
+ `delegate[<service>]:write[<repo_id>]` &mdash; for example
  `delegate[https://on-stage.copyrighthub.org]:write[5e7c2be8f9f8dc8456f61db81e01523e]`
  would be requested to onboard assets to the repository with UUID
  `5e7c2be8f9f8dc8456f61db81e01523e`

To use the returned token in an onboarding request, include the token
in the request `Authorization` header preceded by `Bearer`, see the
examples below.

### Service and resource IDs

UUIDs are used throughout OPP to identify entities including internal
and external services and repositories.

UUIDs for your organisation's application clients and repositories can
be found from the Accounts Service web UI, see
[How to create and manage accounts, services, and users](https://github.com/openpermissions/accounts-srv/blob/master/documents/markdown/how-to-register.md).

OPP service IDs can be discovered by querying the service endpoints,
for example:

```
curl https://on-stage.copyrighthub.org/v1/onboarding
{"status": 200, "data": {"service_name": "Open Permissions Platform Onboarding Service", "hub_id": "hub1", "version": "1.0.0", "default_resolver_id": "openpermissions.org", "service_id": "5e7c2be8f9f8dc8456f61db81e004d32"}}
```

Token scopes accept either the service UUID or URL, for example the
staging Onboarding service URL:

```
https://on-stage.copyrighthub.org
```

## Token request examples

The following examples show how to request tokens from the OPP
Authentication staging service `https://auth-stage.copyrighthub.org`
where:

+ `<client>` is the service ID of the calling application client or
  external service, see [Client credentials](#client-credentials)
+ `<secret>` is the secret of the calling application client or
  external service, see [Client credentials](#client-credentials)

Note that client credentials should be included in the `Authorization`
header, as shown, and **not** the request body or URI.

### `read` token request and usage

>Always use staging service endpoints for test and development.

A `read` token allows a client to read a resource for which it has
read permission, for example a repository, or an OPP endpoint that
supports read requests, for example `/v1/onboarding/capabilities`.

Because `read` (unqualified) is the default token scope, a scope does
not need to be specified.

Where `<client>` is a service client UUID, for example
`fe132d576e24d5cea5f3136a0e00e51a` and `<secret>` is a secret UUID
`ssVRCe9nncpfd0lk4jJv6f4rzHm63i` the cURL command line:

```curl
curl --user <client>:<secret> --data "grant_type=client_credentials" https://auth-stage.copyrighthub.org/v1/auth/token
```

returns a `read` token:

```
{"status": 200, "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnQiOnsic2VydmljZV90eXBlIjoiZXh0ZXJuYWwiLCJvcmdhbmlzYXRpb25faWQiOiI1ZTdjMmJlOGY5ZjhkYzg0NTZmNjFkYjgxZTAxMTc4YiIsImlkIjoiNWU3YzJiZThmOWY4ZGM4NDU2ZjYxZGI4MWUwMTNiMTEifSwiZGVsZWdhdGUiOmZhbHNlLCJhdWQiOiJhdXRoLXN0YWdlLmNvcHlyaWdodGh1Yi5vcmcvdmVyaWZ5IiwiZXhwIjoxNDYwMTA4MTcyLCJpc3MiOiJhdXRoLXN0YWdlLmNvcHlyaWdodGh1Yi5vcmcvdG9rZW4iLCJzY29wZSI6InJlYWQiLCJncmFudF90eXBlIjoiY2xpZW50X2NyZWRlbnRpYWxzIiwic3ViIjoiNWU3YzJiZThmOWY4ZGM4NDU2ZjYxZGI4MWUwMTNiMTEifQ.doUva9iX2GNqSe28XqmNS7uVaw801vsae_TPUDtPKzD7bTzOwvj_0nq7uNWnm-UFAyVtBmphtAAzNhnXR4mhb86C7__kP5RfA8TY_8cnkbPxFFQu6ZnCDJlq3X3SFQf5WIWJgRoQOI67MD3MpSpf1SMNlYT4DnIIYWoAsLJUa6aPOqG0-E8v0z1YFEbiCnZV38_FYaE1HU3biOcW_JFmjHIIqTIe0uuv-6-rSqDOsj8C36i403yeHJ5i47QloNyK5L8w2CQ2UlcjD5gTK7JzFTaJ0u1t8qfAsPsuyJslQP0n5RmeTboq47rVPOi1dtAG-mfOhqzyphmwUV_fxW8Kgw", "token_type": "bearer", "expiry": 1460108172}
```
or if the credentials are rejected:

```
{"status": 401, "errors": [{"source": "authentication", "message": "Unauthenticated"}]}
```

Use the token to read a resource, for example:

```curl
curl --header "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnQiOnsic2VydmljZV90eXBlIjoiZXh0ZXJuYWwiLCJvcmdhbmlzYXRpb25faWQiOiI1ZTdjMmJlOGY5ZjhkYzg0NTZmNjFkYjgxZTAxMTc4YiIsImlkIjoiNWU3YzJiZThmOWY4ZGM4NDU2ZjYxZGI4MWUwMTNiMTEifSwiZGVsZWdhdGUiOmZhbHNlLCJhdWQiOiJhdXRoLXN0YWdlLmNvcHlyaWdodGh1Yi5vcmcvdmVyaWZ5IiwiZXhwIjoxNDYwMTE4NDU0LCJpc3MiOiJhdXRoLXN0YWdlLmNvcHlyaWdodGh1Yi5vcmcvdG9rZW4iLCJzY29wZSI6InJlYWQiLCJncmFudF90eXBlIjoiY2xpZW50X2NyZWRlbnRpYWxzIiwic3ViIjoiNWU3YzJiZThmOWY4ZGM4NDU2ZjYxZGI4MWUwMTNiMTEifQ.KWVCSpPv1oaLQ1aX2emYqqUnmuBRRbKGwndZhq_GwGmN3cLnXp1bw7OubpafRSruweIYxQ_QYiHTRSOAXziICFgU876jWuvg0yCzFiwPwnLT1CkFM_7dB46Qcrf0AhlYp79KLMbvSYe8xpBAVegpeiWKxqOWPC6tOvhaK5BqUn18iFuUM8ZpSU69Y0nxArLpKct78G0TpNr4eYgKvW0ZDePp0YT4AqwndeMbbHaqKAKsjK8sMMd3lglVxB7wuVOF3XRCgrH7zyvTaL8Y7fg0kusvXcbM66uIR5ZzasL5XlxYkN9H0UYnTl8B9x3lges2K2cINOyESNyBCF3Z0LcAKg" https://on-stage.copyrighthub.org/v1/onboarding/capabilities
{"status": 200, "data": {"max_post_body_size": 3000000}}
```

### Delegated `write` token request and usage

>Always use staging service endpoints for test and development.

To onboard to an OPP repository, the calling client must provide in
the API call a token that delegates a `write` permission for the client
repository to the Repository service.

For example, where `5e7c2be8f9f8dc8456f61db81e01523e` is the UUID of a
repository registered to the application client, request a token with
the following scope:

````
delegate[https://on-stage.copyrighthub.org/v1/onboarding]:write[5e7c2be8f9f8dc8456f61db81e01523e]
```

The cURL command line where `<repo_id>` is a valid repository UUID,
`<client>` is a service client UUID, and `<secret>` is a secret UUID:

```curl
curl --user <client>:<secret> --data "grant_type=client_credentials&scope=delegate[https://on-stage.copyrighthub.org]:write[<repo_id>]" https://auth-stage.copyrighthub.org/v1/auth/token
```

returns a delegated `write` token:

```
{"status": 200, "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnQiOnsic2VydmljZV90eXBlIjoiZXh0ZXJuYWwiLCJvcmdhbmlzYXRpb25faWQiOiI1ZTdjMmJlOGY5ZjhkYzg0NTZmNjFkYjgxZTAxMTc4YiIsImlkIjoiNWU3YzJiZThmOWY4ZGM4NDU2ZjYxZGI4MWUwMTNiMTEifSwiZGVsZWdhdGUiOmZhbHNlLCJhdWQiOiJhdXRoLXN0YWdlLmNvcHlyaWdodGh1Yi5vcmcvdmVyaWZ5IiwiZXhwIjoxNDYwMTIwMTI3LCJpc3MiOiJhdXRoLXN0YWdlLmNvcHlyaWdodGh1Yi5vcmcvdG9rZW4iLCJzY29wZSI6ImRlbGVnYXRlW2h0dHBzOi8vb24tc3RhZ2UuY29weXJpZ2h0aHViLm9yZ106d3JpdGVbNWU3YzJiZThmOWY4ZGM4NDU2ZjYxZGI4MWUwMTUyM2VdIiwiZ3JhbnRfdHlwZSI6ImNsaWVudF9jcmVkZW50aWFscyIsInN1YiI6IjVlN2MyYmU4ZjlmOGRjODQ1NmY2MWRiODFlMDEzYjExIn0.q66zEdcX2iW-Kq87vLp7glhTBgIUHQakoCpM8tuMxJq9yo4e5fILO-mIk8fVS-gIqcKJjX-fJh_ySqN2Xiwz-VCx33XySETGKdgerEofzZVuiE1Il-FuSBYSSLUEHIQ65f2ssBwJ209ipU4X_gfJcogWZ4HM0uKRHCBlBJuxmWU97-ERSyQJSqZdLHzslAO8QpPFyx0ZBV2xD-TA0KtL5gauK5vwRpaJoYM4Y1h3AZypIsbOrRuqjyKasiwQ_bT0Ktc-a7Rmv-hOYQVO1TuqJwwiwz-XNKSQ8Cm9tTipKA9gTQLPnUGxF7mVUjcqZuM5F4UK1YIUdk13uFrBvDs80g", "token_type": "bearer", "expiry": 1460120127}
```

that can be used to onboard assets to the specified repository.

For an onboading example in Python, including a token request with
delegated `write` scope, which is then used to onboard an asset, see [How to use the Onboarding Service](https://github.com/openpermissions/onboarding-srv/blob/master/documents/markdown/how-to-onboard.md).

<!-- Copyright Notice -->
<a rel="license" href="http://creativecommons.org/licenses/by/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/80x15.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.
