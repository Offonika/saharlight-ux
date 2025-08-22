# diabetes_sdk.DefaultApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**api_reminders_post_reminders_post**](DefaultApi.md#api_reminders_post_reminders_post) | **POST** /reminders | Api Reminders Post
[**api_reminders_reminders_get**](DefaultApi.md#api_reminders_reminders_get) | **GET** /reminders | Api Reminders
[**create_user_user_post**](DefaultApi.md#create_user_user_post) | **POST** /user | Create User
[**delete_history_history_record_id_delete**](DefaultApi.md#delete_history_history_record_id_delete) | **DELETE** /history/{record_id} | Delete History
[**get_analytics_analytics_get**](DefaultApi.md#get_analytics_analytics_get) | **GET** /analytics | Get Analytics
[**get_history_history_get**](DefaultApi.md#get_history_history_get) | **GET** /history | Get History
[**get_stats_stats_get**](DefaultApi.md#get_stats_stats_get) | **GET** /stats | Get Stats
[**get_timezone_timezone_get**](DefaultApi.md#get_timezone_timezone_get) | **GET** /timezone | Get Timezone
[**post_history_history_post**](DefaultApi.md#post_history_history_post) | **POST** /history | Post History
[**profile_self_profile_self_get**](DefaultApi.md#profile_self_profile_self_get) | **GET** /profile/self | Profile Self
[**profiles_get_profiles_get**](DefaultApi.md#profiles_get_profiles_get) | **GET** /profiles | Profiles Get
[**profiles_post_profiles_post**](DefaultApi.md#profiles_post_profiles_post) | **POST** /profiles | Profiles Post
[**put_timezone_timezone_put**](DefaultApi.md#put_timezone_timezone_put) | **PUT** /timezone | Put Timezone


# **api_reminders_post_reminders_post**
> Dict[str, object] api_reminders_post_reminders_post(reminder_schema, x_telegram_init_data=x_telegram_init_data)

Api Reminders Post

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
    api_instance = diabetes_sdk.DefaultApi(api_client)
    reminder_schema = diabetes_sdk.ReminderSchema() # ReminderSchema | 
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Api Reminders Post
        api_response = api_instance.api_reminders_post_reminders_post(reminder_schema, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->api_reminders_post_reminders_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->api_reminders_post_reminders_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **reminder_schema** | [**ReminderSchema**](ReminderSchema.md)|  | 
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

# **api_reminders_reminders_get**
> List[ReminderSchema] api_reminders_reminders_get(telegram_id, id=id, x_telegram_init_data=x_telegram_init_data)

Api Reminders

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
    api_instance = diabetes_sdk.DefaultApi(api_client)
    telegram_id = 56 # int | 
    id = 56 # int |  (optional)
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Api Reminders
        api_response = api_instance.api_reminders_reminders_get(telegram_id, id=id, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->api_reminders_reminders_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->api_reminders_reminders_get: %s\n" % e)
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

# **create_user_user_post**
> Dict[str, Optional[str]] create_user_user_post(web_user, x_telegram_init_data=x_telegram_init_data)

Create User

Ensure a user exists in the database.

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.web_user import WebUser
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
    web_user = diabetes_sdk.WebUser() # WebUser | 
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Create User
        api_response = api_instance.create_user_user_post(web_user, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->create_user_user_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->create_user_user_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **web_user** | [**WebUser**](WebUser.md)|  | 
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

**Dict[str, Optional[str]]**

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

# **delete_history_history_record_id_delete**
> Dict[str, Optional[str]] delete_history_history_record_id_delete(record_id, x_telegram_init_data=x_telegram_init_data)

Delete History

Delete a history record after verifying ownership.

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
    record_id = 'record_id_example' # str | 
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Delete History
        api_response = api_instance.delete_history_history_record_id_delete(record_id, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->delete_history_history_record_id_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->delete_history_history_record_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **record_id** | **str**|  | 
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

**Dict[str, Optional[str]]**

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

# **get_analytics_analytics_get**
> List[AnalyticsPoint] get_analytics_analytics_get(telegram_id, x_telegram_init_data=x_telegram_init_data)

Get Analytics

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.analytics_point import AnalyticsPoint
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
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Get Analytics
        api_response = api_instance.get_analytics_analytics_get(telegram_id, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->get_analytics_analytics_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_analytics_analytics_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

[**List[AnalyticsPoint]**](AnalyticsPoint.md)

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

# **get_history_history_get**
> List[HistoryRecordSchemaOutput] get_history_history_get(x_telegram_init_data=x_telegram_init_data)

Get History

Return history records for the authenticated user.

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.history_record_schema_output import HistoryRecordSchemaOutput
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
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Get History
        api_response = api_instance.get_history_history_get(x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->get_history_history_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_history_history_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

[**List[HistoryRecordSchemaOutput]**](HistoryRecordSchemaOutput.md)

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

# **get_stats_stats_get**
> DayStats get_stats_stats_get(telegram_id, x_telegram_init_data=x_telegram_init_data)

Get Stats

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.day_stats import DayStats
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
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Get Stats
        api_response = api_instance.get_stats_stats_get(telegram_id, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->get_stats_stats_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_stats_stats_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

[**DayStats**](DayStats.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response. Returns statistics for the day. |  -  |
**204** | No Content - no statistics available. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_timezone_timezone_get**
> Dict[str, Optional[str]] get_timezone_timezone_get(x_telegram_init_data=x_telegram_init_data)

Get Timezone

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
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Get Timezone
        api_response = api_instance.get_timezone_timezone_get(x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->get_timezone_timezone_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_timezone_timezone_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

**Dict[str, Optional[str]]**

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

# **post_history_history_post**
> Dict[str, Optional[str]] post_history_history_post(history_record_schema_input, x_telegram_init_data=x_telegram_init_data)

Post History

Save or update a history record in the database.

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.history_record_schema_input import HistoryRecordSchemaInput
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
    history_record_schema_input = diabetes_sdk.HistoryRecordSchemaInput() # HistoryRecordSchemaInput | 
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Post History
        api_response = api_instance.post_history_history_post(history_record_schema_input, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->post_history_history_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->post_history_history_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **history_record_schema_input** | [**HistoryRecordSchemaInput**](HistoryRecordSchemaInput.md)|  | 
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

**Dict[str, Optional[str]]**

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

# **profile_self_profile_self_get**
> UserContext profile_self_profile_self_get(x_telegram_init_data=x_telegram_init_data)

Profile Self

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.user_context import UserContext
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
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Profile Self
        api_response = api_instance.profile_self_profile_self_get(x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->profile_self_profile_self_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->profile_self_profile_self_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

[**UserContext**](UserContext.md)

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

# **profiles_get_profiles_get**
> ProfileSchema profiles_get_profiles_get(telegram_id)

Profiles Get

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.profile_schema import ProfileSchema
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
        # Profiles Get
        api_response = api_instance.profiles_get_profiles_get(telegram_id)
        print("The response of DefaultApi->profiles_get_profiles_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->profiles_get_profiles_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | 

### Return type

[**ProfileSchema**](ProfileSchema.md)

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

# **profiles_post_profiles_post**
> Dict[str, Optional[str]] profiles_post_profiles_post(profile_schema)

Profiles Post

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.profile_schema import ProfileSchema
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
    profile_schema = diabetes_sdk.ProfileSchema() # ProfileSchema | 

    try:
        # Profiles Post
        api_response = api_instance.profiles_post_profiles_post(profile_schema)
        print("The response of DefaultApi->profiles_post_profiles_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->profiles_post_profiles_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **profile_schema** | [**ProfileSchema**](ProfileSchema.md)|  | 

### Return type

**Dict[str, Optional[str]]**

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

# **put_timezone_timezone_put**
> Dict[str, Optional[str]] put_timezone_timezone_put(timezone, x_telegram_init_data=x_telegram_init_data)

Put Timezone

### Example


```python
import diabetes_sdk
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
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Put Timezone
        api_response = api_instance.put_timezone_timezone_put(timezone, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->put_timezone_timezone_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->put_timezone_timezone_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **timezone** | [**Timezone**](Timezone.md)|  | 
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

**Dict[str, Optional[str]]**

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

