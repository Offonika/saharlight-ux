# diabetes_sdk.RemindersApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**reminders_delete**](RemindersApi.md#reminders_delete) | **DELETE** /reminders | Reminders Delete
[**reminders_get**](RemindersApi.md#reminders_get) | **GET** /reminders | Reminders Get
[**reminders_id_get**](RemindersApi.md#reminders_id_get) | **GET** /reminders/{id} | Reminders Id Get
[**reminders_patch**](RemindersApi.md#reminders_patch) | **PATCH** /reminders | Reminders Patch
[**reminders_post**](RemindersApi.md#reminders_post) | **POST** /reminders | Reminders Post


# **reminders_delete**
> Dict[str, object] reminders_delete(telegram_id, id)

Reminders Delete

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "http://localhost"
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
    api_instance = diabetes_sdk.RemindersApi(api_client)
    telegram_id = 56 # int | 
    id = 56 # int | 

    try:
        # Reminders Delete
        api_response = api_instance.reminders_delete(telegram_id, id)
        print("The response of RemindersApi->reminders_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RemindersApi->reminders_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 
 **id** | **int**|  | 

### Return type

**Dict[str, object]**

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
**404** | Reminder not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reminders_get**
> List[ReminderSchema] reminders_get(telegram_id)

Reminders Get

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.reminder_schema import ReminderSchema
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "http://localhost"
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
    api_instance = diabetes_sdk.RemindersApi(api_client)
    telegram_id = 56 # int | 

    try:
        # Reminders Get
        api_response = api_instance.reminders_get(telegram_id)
        print("The response of RemindersApi->reminders_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RemindersApi->reminders_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 

### Return type

[**List[ReminderSchema]**](ReminderSchema.md)

### Authorization

[telegramInitData](../README.md#telegramInitData)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response. Returns an array of reminders. An empty array is returned when no reminders exist. |  -  |
**422** | Validation Error |  -  |
**404** | Reminder not found or telegramId mismatch |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reminders_id_get**
> ReminderSchema reminders_id_get(id, telegram_id)

Reminders Id Get

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.reminder_schema import ReminderSchema
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "http://localhost"
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
    api_instance = diabetes_sdk.RemindersApi(api_client)
    id = 56 # int | 
    telegram_id = 56 # int | 

    try:
        # Reminders Id Get
        api_response = api_instance.reminders_id_get(id, telegram_id)
        print("The response of RemindersApi->reminders_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RemindersApi->reminders_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **int**|  | 
 **telegram_id** | **int**|  | 

### Return type

[**ReminderSchema**](ReminderSchema.md)

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
**404** | Reminder not found or telegramId mismatch |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reminders_patch**
> Dict[str, object] reminders_patch(reminder)

Reminders Patch

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.reminder_schema import ReminderSchema
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "http://localhost"
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
    api_instance = diabetes_sdk.RemindersApi(api_client)
    reminder = diabetes_sdk.ReminderSchema() # ReminderSchema | 

    try:
        # Reminders Patch
        api_response = api_instance.reminders_patch(reminder)
        print("The response of RemindersApi->reminders_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RemindersApi->reminders_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **reminder** | [**ReminderSchema**](ReminderSchema.md)|  | 

### Return type

**Dict[str, object]**

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

# **reminders_post**
> Dict[str, object] reminders_post(reminder)

Reminders Post

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.reminder_schema import ReminderSchema
from diabetes_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = diabetes_sdk.Configuration(
    host = "http://localhost"
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
    api_instance = diabetes_sdk.RemindersApi(api_client)
    reminder = diabetes_sdk.ReminderSchema() # ReminderSchema | 

    try:
        # Reminders Post
        api_response = api_instance.reminders_post(reminder)
        print("The response of RemindersApi->reminders_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RemindersApi->reminders_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **reminder** | [**ReminderSchema**](ReminderSchema.md)|  | 

### Return type

**Dict[str, object]**

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

