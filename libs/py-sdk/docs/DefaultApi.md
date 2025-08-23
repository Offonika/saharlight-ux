# diabetes_sdk.DefaultApi

All URIs are relative to */api*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_user_user_post**](DefaultApi.md#create_user_user_post) | **POST** /user | Create User
[**get_analytics_analytics_get**](DefaultApi.md#get_analytics_analytics_get) | **GET** /analytics | Get Analytics
[**get_role_user_user_id_role_get**](DefaultApi.md#get_role_user_user_id_role_get) | **GET** /user/{user_id}/role | Get Role
[**get_stats_stats_get**](DefaultApi.md#get_stats_stats_get) | **GET** /stats | Get Stats
[**get_timezone_timezone_get**](DefaultApi.md#get_timezone_timezone_get) | **GET** /timezone | Get Timezone
[**health_get**](DefaultApi.md#health_get) | **GET** /health | Health
[**profile_self_profile_self_get**](DefaultApi.md#profile_self_profile_self_get) | **GET** /profile/self | Profile Self
[**put_role_user_user_id_role_put**](DefaultApi.md#put_role_user_user_id_role_put) | **PUT** /user/{user_id}/role | Put Role
[**put_timezone_timezone_put**](DefaultApi.md#put_timezone_timezone_put) | **PUT** /timezone | Put Timezone


# **create_user_user_post**
> Dict[str, str] create_user_user_post(web_user)

Create User

Ensure a user exists in the database.

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.web_user import WebUser
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to /api
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "/api"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: telegramInitData
configuration.api_key['telegramInitData'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['telegramInitData'] = 'Bearer'

# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)
    web_user = diabetes_sdk.WebUser() # WebUser | 

    try:
        # Create User
        api_response = api_instance.create_user_user_post(web_user)
        print("The response of DefaultApi->create_user_user_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->create_user_user_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **web_user** | [**WebUser**](WebUser.md)|  | 

### Return type

**Dict[str, str]**

### Authorization

[telegramInitData](../README.md#telegramInitData)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_analytics_analytics_get**
> List[AnalyticsPoint] get_analytics_analytics_get(telegram_id)

Get Analytics

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.analytics_point import AnalyticsPoint
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to /api
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "/api"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: telegramInitData
configuration.api_key['telegramInitData'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['telegramInitData'] = 'Bearer'

# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)
    telegram_id = 56 # int | 

    try:
        # Get Analytics
        api_response = api_instance.get_analytics_analytics_get(telegram_id)
        print("The response of DefaultApi->get_analytics_analytics_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_analytics_analytics_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 

### Return type

[**List[AnalyticsPoint]**](AnalyticsPoint.md)

### Authorization

[telegramInitData](../README.md#telegramInitData)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**403** | Forbidden |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_role_user_user_id_role_get**
> RoleSchema get_role_user_user_id_role_get(user_id)

Get Role

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.role_schema import RoleSchema
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to /api
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "/api"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: telegramInitData
configuration.api_key['telegramInitData'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['telegramInitData'] = 'Bearer'

# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)
    user_id = 56 # int | 

    try:
        # Get Role
        api_response = api_instance.get_role_user_user_id_role_get(user_id)
        print("The response of DefaultApi->get_role_user_user_id_role_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_role_user_user_id_role_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **user_id** | **int**|  | 

### Return type

[**RoleSchema**](RoleSchema.md)

### Authorization

[telegramInitData](../README.md#telegramInitData)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_stats_stats_get**
> DayStats get_stats_stats_get(telegram_id)

Get Stats

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.day_stats import DayStats
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to /api
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "/api"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: telegramInitData
configuration.api_key['telegramInitData'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['telegramInitData'] = 'Bearer'

# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)
    telegram_id = 56 # int | 

    try:
        # Get Stats
        api_response = api_instance.get_stats_stats_get(telegram_id)
        print("The response of DefaultApi->get_stats_stats_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_stats_stats_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 

### Return type

[**DayStats**](DayStats.md)

### Authorization

[telegramInitData](../README.md#telegramInitData)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response. Returns statistics for the day. |  -  |
**204** | No Content - no statistics available. |  -  |
**403** | Forbidden |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_timezone_timezone_get**
> Dict[str, str] get_timezone_timezone_get()

Get Timezone

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to /api
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "/api"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: telegramInitData
configuration.api_key['telegramInitData'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['telegramInitData'] = 'Bearer'

# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)

    try:
        # Get Timezone
        api_response = api_instance.get_timezone_timezone_get()
        print("The response of DefaultApi->get_timezone_timezone_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_timezone_timezone_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**Dict[str, str]**

### Authorization

[telegramInitData](../README.md#telegramInitData)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **health_get**
> Dict[str, str] health_get()

Health

### Example


```python
import diabetes_sdk
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to /api
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "/api"
)


# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)

    try:
        # Health
        api_response = api_instance.health_get()
        print("The response of DefaultApi->health_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->health_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**Dict[str, str]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **profile_self_profile_self_get**
> UserContext profile_self_profile_self_get()

Profile Self

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.user_context import UserContext
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to /api
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "/api"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: telegramInitData
configuration.api_key['telegramInitData'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['telegramInitData'] = 'Bearer'

# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)

    try:
        # Profile Self
        api_response = api_instance.profile_self_profile_self_get()
        print("The response of DefaultApi->profile_self_profile_self_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->profile_self_profile_self_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**UserContext**](UserContext.md)

### Authorization

[telegramInitData](../README.md#telegramInitData)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **put_role_user_user_id_role_put**
> RoleSchema put_role_user_user_id_role_put(user_id, role_schema)

Put Role

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.role_schema import RoleSchema
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to /api
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "/api"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: telegramInitData
configuration.api_key['telegramInitData'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['telegramInitData'] = 'Bearer'

# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)
    user_id = 56 # int | 
    role_schema = diabetes_sdk.RoleSchema() # RoleSchema | 

    try:
        # Put Role
        api_response = api_instance.put_role_user_user_id_role_put(user_id, role_schema)
        print("The response of DefaultApi->put_role_user_user_id_role_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->put_role_user_user_id_role_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **user_id** | **int**|  | 
 **role_schema** | [**RoleSchema**](RoleSchema.md)|  | 

### Return type

[**RoleSchema**](RoleSchema.md)

### Authorization

[telegramInitData](../README.md#telegramInitData)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **put_timezone_timezone_put**
> Dict[str, str] put_timezone_timezone_put(timezone)

Put Timezone

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.timezone import Timezone
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to /api
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "/api"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: telegramInitData
configuration.api_key['telegramInitData'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['telegramInitData'] = 'Bearer'

# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)
    timezone = diabetes_sdk.Timezone() # Timezone | 

    try:
        # Put Timezone
        api_response = api_instance.put_timezone_timezone_put(timezone)
        print("The response of DefaultApi->put_timezone_timezone_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->put_timezone_timezone_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **timezone** | [**Timezone**](Timezone.md)|  | 

### Return type

**Dict[str, str]**

### Authorization

[telegramInitData](../README.md#telegramInitData)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

