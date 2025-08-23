# diabetes_sdk.RemindersApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**reminders_delete**](RemindersApi.md#reminders_delete) | **DELETE** /reminders | Reminders Delete
[**reminders_get**](RemindersApi.md#reminders_get) | **GET** /reminders | Reminders Get
[**reminders_patch**](RemindersApi.md#reminders_patch) | **PATCH** /reminders | Reminders Patch
[**reminders_post**](RemindersApi.md#reminders_post) | **POST** /reminders | Reminders Post


# **reminders_delete**
> Dict[str, object] reminders_delete(telegram_id, id, x_telegram_init_data=x_telegram_init_data)

Reminders Delete

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
    api_instance = diabetes_sdk.RemindersApi(api_client)
    telegram_id = 56 # int | 
    id = 56 # int | 
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Reminders Delete
        api_response = api_instance.reminders_delete(telegram_id, id, x_telegram_init_data=x_telegram_init_data)
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
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

**Dict[str, object]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reminders_get**
> List[ReminderSchema] reminders_get(telegram_id, id=id, x_telegram_init_data=x_telegram_init_data)

Reminders Get

### Example


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


# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.RemindersApi(api_client)
    telegram_id = 56 # int | 
    id = 56 # int |  (optional)
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Reminders Get
        api_response = api_instance.reminders_get(telegram_id, id=id, x_telegram_init_data=x_telegram_init_data)
        print("The response of RemindersApi->reminders_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RemindersApi->reminders_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 
 **id** | **int**|  | [optional] 
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

[**List[ReminderSchema]**](ReminderSchema.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response. Returns an array of reminders. An empty array is returned when no reminders exist. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reminders_patch**
> Dict[str, object] reminders_patch(reminder, x_telegram_init_data=x_telegram_init_data)

Reminders Patch

### Example


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


# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.RemindersApi(api_client)
    reminder = diabetes_sdk.ReminderSchema() # ReminderSchema | 
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Reminders Patch
        api_response = api_instance.reminders_patch(reminder, x_telegram_init_data=x_telegram_init_data)
        print("The response of RemindersApi->reminders_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RemindersApi->reminders_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **reminder** | [**ReminderSchema**](ReminderSchema.md)|  | 
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

**Dict[str, object]**

### Authorization

No authorization required

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
> Dict[str, object] reminders_post(reminder, x_telegram_init_data=x_telegram_init_data)

Reminders Post

### Example


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


# Enter a context with an instance of the API client
with diabetes_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = diabetes_sdk.RemindersApi(api_client)
    reminder = diabetes_sdk.ReminderSchema() # ReminderSchema | 
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Reminders Post
        api_response = api_instance.reminders_post(reminder, x_telegram_init_data=x_telegram_init_data)
        print("The response of RemindersApi->reminders_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RemindersApi->reminders_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **reminder** | [**ReminderSchema**](ReminderSchema.md)|  | 
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

**Dict[str, object]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

