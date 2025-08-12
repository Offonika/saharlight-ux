# diabetes_sdk.DefaultApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**api_reminders_get**](DefaultApi.md#api_reminders_get) | **GET** /api/reminders | List or retrieve reminders
[**api_reminders_post**](DefaultApi.md#api_reminders_post) | **POST** /api/reminders | Save reminder
[**health_get**](DefaultApi.md#health_get) | **GET** /health | Health check
[**profiles_get**](DefaultApi.md#profiles_get) | **GET** /profiles | Get user profile
[**profiles_post**](DefaultApi.md#profiles_post) | **POST** /profiles | Save user profile
[**timezone_post**](DefaultApi.md#timezone_post) | **POST** /timezone | Save timezone


# **api_reminders_get**
> ApiRemindersGet200Response api_reminders_get(telegram_id, id=id)

List or retrieve reminders

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.api_reminders_get200_response import ApiRemindersGet200Response
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)
    telegram_id = 56 # int | 
    id = 56 # int |  (optional)

    try:
        # List or retrieve reminders
        api_response = api_instance.api_reminders_get(telegram_id, id=id)
        print("The response of DefaultApi->api_reminders_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->api_reminders_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 
 **id** | **int**|  | [optional] 

### Return type

[**ApiRemindersGet200Response**](ApiRemindersGet200Response.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **api_reminders_post**
> ApiRemindersPost200Response api_reminders_post(reminder)

Save reminder

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.api_reminders_post200_response import ApiRemindersPost200Response
from diabetes_sdk.models.reminder import Reminder
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)
    reminder = diabetes_sdk.Reminder() # Reminder | 

    try:
        # Save reminder
        api_response = api_instance.api_reminders_post(reminder)
        print("The response of DefaultApi->api_reminders_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->api_reminders_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **reminder** | [**Reminder**](Reminder.md)|  | 

### Return type

[**ApiRemindersPost200Response**](ApiRemindersPost200Response.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **health_get**
> Status health_get()

Health check

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.status import Status
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)

    try:
        # Health check
        api_response = api_instance.health_get()
        print("The response of DefaultApi->health_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->health_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**Status**](Status.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **profiles_get**
> Profile profiles_get(telegram_id)

Get user profile

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.profile import Profile
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)
    telegram_id = 56 # int | 

    try:
        # Get user profile
        api_response = api_instance.profiles_get(telegram_id)
        print("The response of DefaultApi->profiles_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->profiles_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 

### Return type

[**Profile**](Profile.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **profiles_post**
> Status profiles_post(profile)

Save user profile

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.profile import Profile
from diabetes_sdk.models.status import Status
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)
    profile = diabetes_sdk.Profile() # Profile | 

    try:
        # Save user profile
        api_response = api_instance.profiles_post(profile)
        print("The response of DefaultApi->profiles_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->profiles_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **profile** | [**Profile**](Profile.md)|  | 

### Return type

[**Status**](Status.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **timezone_post**
> Status timezone_post(timezone)

Save timezone

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.status import Status
from diabetes_sdk.models.timezone import Timezone
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.DefaultApi(api_client)
    timezone = diabetes_sdk.Timezone() # Timezone | 

    try:
        # Save timezone
        api_response = api_instance.timezone_post(timezone)
        print("The response of DefaultApi->timezone_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->timezone_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **timezone** | [**Timezone**](Timezone.md)|  | 

### Return type

[**Status**](Status.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

