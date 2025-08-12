# diabetes_sdk.DefaultApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**auth_post**](DefaultApi.md#auth_post) | **POST** /auth | Authenticate user
[**entries_get**](DefaultApi.md#entries_get) | **GET** /entries | List or retrieve entries
[**entries_post**](DefaultApi.md#entries_post) | **POST** /entries | Save entry
[**profiles_get**](DefaultApi.md#profiles_get) | **GET** /profiles | Get user profile
[**profiles_post**](DefaultApi.md#profiles_post) | **POST** /profiles | Save user profile
[**reminders_get**](DefaultApi.md#reminders_get) | **GET** /reminders | List or retrieve reminders
[**reminders_post**](DefaultApi.md#reminders_post) | **POST** /reminders | Save reminder
[**reports_get**](DefaultApi.md#reports_get) | **GET** /reports | Generate report


# **auth_post**
> AuthResponse auth_post(auth_request)

Authenticate user

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.auth_request import AuthRequest
from diabetes_sdk.models.auth_response import AuthResponse
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
    auth_request = diabetes_sdk.AuthRequest() # AuthRequest | 

    try:
        # Authenticate user
        api_response = api_instance.auth_post(auth_request)
        print("The response of DefaultApi->auth_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->auth_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **auth_request** | [**AuthRequest**](AuthRequest.md)|  | 

### Return type

[**AuthResponse**](AuthResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Authenticated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **entries_get**
> EntriesGet200Response entries_get(telegram_id, id=id)

List or retrieve entries

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.entries_get200_response import EntriesGet200Response
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
        # List or retrieve entries
        api_response = api_instance.entries_get(telegram_id, id=id)
        print("The response of DefaultApi->entries_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->entries_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 
 **id** | **int**|  | [optional] 

### Return type

[**EntriesGet200Response**](EntriesGet200Response.md)

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

# **entries_post**
> EntriesPost200Response entries_post(entry)

Save entry

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.entries_post200_response import EntriesPost200Response
from diabetes_sdk.models.entry import Entry
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
    entry = diabetes_sdk.Entry() # Entry | 

    try:
        # Save entry
        api_response = api_instance.entries_post(entry)
        print("The response of DefaultApi->entries_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->entries_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **entry** | [**Entry**](Entry.md)|  | 

### Return type

[**EntriesPost200Response**](EntriesPost200Response.md)

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

# **reminders_get**
> RemindersGet200Response reminders_get(telegram_id, id=id)

List or retrieve reminders

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.reminders_get200_response import RemindersGet200Response
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
        api_response = api_instance.reminders_get(telegram_id, id=id)
        print("The response of DefaultApi->reminders_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->reminders_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 
 **id** | **int**|  | [optional] 

### Return type

[**RemindersGet200Response**](RemindersGet200Response.md)

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

# **reminders_post**
> EntriesPost200Response reminders_post(reminder)

Save reminder

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.entries_post200_response import EntriesPost200Response
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
        api_response = api_instance.reminders_post(reminder)
        print("The response of DefaultApi->reminders_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->reminders_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **reminder** | [**Reminder**](Reminder.md)|  | 

### Return type

[**EntriesPost200Response**](EntriesPost200Response.md)

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

# **reports_get**
> bytearray reports_get(telegram_id, period_days=period_days)

Generate report

### Example


```python
import diabetes_sdk
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
    period_days = 56 # int |  (optional)

    try:
        # Generate report
        api_response = api_instance.reports_get(telegram_id, period_days=period_days)
        print("The response of DefaultApi->reports_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->reports_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 
 **period_days** | **int**|  | [optional] 

### Return type

**bytearray**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/pdf

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | PDF report |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

