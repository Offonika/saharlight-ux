# diabetes_sdk.DefaultApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_user_user_post**](DefaultApi.md#create_user_user_post) | **POST** /user | Create User
[**delete_reminder_api_reminders_delete**](DefaultApi.md#delete_reminder_api_reminders_delete) | **DELETE** /api/reminders | Delete Reminder
[**get_analytics_api_analytics_get**](DefaultApi.md#get_analytics_api_analytics_get) | **GET** /api/analytics | Get Analytics
[**get_reminders_api_reminders_get**](DefaultApi.md#get_reminders_api_reminders_get) | **GET** /api/reminders | Get Reminders
[**get_role_user_user_id_role_get**](DefaultApi.md#get_role_user_user_id_role_get) | **GET** /user/{user_id}/role | Get Role
[**get_stats_api_stats_get**](DefaultApi.md#get_stats_api_stats_get) | **GET** /api/stats | Get Stats
[**get_timezone_timezone_get**](DefaultApi.md#get_timezone_timezone_get) | **GET** /timezone | Get Timezone
[**patch_reminder_api_reminders_patch**](DefaultApi.md#patch_reminder_api_reminders_patch) | **PATCH** /api/reminders | Patch Reminder
[**post_reminder_api_reminders_post**](DefaultApi.md#post_reminder_api_reminders_post) | **POST** /api/reminders | Post Reminder
[**profile_self_api_profile_self_get**](DefaultApi.md#profile_self_api_profile_self_get) | **GET** /api/profile/self | Profile Self
[**profile_self_profile_self_get**](DefaultApi.md#profile_self_profile_self_get) | **GET** /profile/self | Profile Self
[**put_role_user_user_id_role_put**](DefaultApi.md#put_role_user_user_id_role_put) | **PUT** /user/{user_id}/role | Put Role
[**put_timezone_timezone_put**](DefaultApi.md#put_timezone_timezone_put) | **PUT** /timezone | Put Timezone


# **create_user_user_post**
> Dict[str, str] create_user_user_post(web_user, x_telegram_init_data=x_telegram_init_data)

Create User

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

**Dict[str, str]**

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

# **delete_reminder_api_reminders_delete**
> Dict[str, str] delete_reminder_api_reminders_delete(telegram_id=telegram_id, telegram_id2=telegram_id2, id=id, x_telegram_init_data=x_telegram_init_data)

Delete Reminder

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
    telegram_id = 56 # int |  (optional)
    telegram_id2 = 56 # int |  (optional)
    id = 56 # int |  (optional)
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Delete Reminder
        api_response = api_instance.delete_reminder_api_reminders_delete(telegram_id=telegram_id, telegram_id2=telegram_id2, id=id, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->delete_reminder_api_reminders_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->delete_reminder_api_reminders_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | [optional] 
 **telegram_id2** | **int**|  | [optional] 
 **id** | **int**|  | [optional] 
 **x_telegram_init_data** | **str**|  | [optional] 

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
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_analytics_api_analytics_get**
> List[AnalyticsPoint] get_analytics_api_analytics_get(telegram_id, x_telegram_init_data=x_telegram_init_data)

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
        api_response = api_instance.get_analytics_api_analytics_get(telegram_id, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->get_analytics_api_analytics_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_analytics_api_analytics_get: %s\n" % e)
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

# **get_reminders_api_reminders_get**
> ResponseGetRemindersApiRemindersGet get_reminders_api_reminders_get(telegram_id=telegram_id, telegram_id2=telegram_id2, id=id, x_telegram_init_data=x_telegram_init_data)

Get Reminders

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.response_get_reminders_api_reminders_get import ResponseGetRemindersApiRemindersGet
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
    telegram_id = 56 # int |  (optional)
    telegram_id2 = 56 # int |  (optional)
    id = 56 # int |  (optional)
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Get Reminders
        api_response = api_instance.get_reminders_api_reminders_get(telegram_id=telegram_id, telegram_id2=telegram_id2, id=id, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->get_reminders_api_reminders_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_reminders_api_reminders_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | [optional] 
 **telegram_id2** | **int**|  | [optional] 
 **id** | **int**|  | [optional] 
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

[**ResponseGetRemindersApiRemindersGet**](ResponseGetRemindersApiRemindersGet.md)

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

# **get_role_user_user_id_role_get**
> RoleSchema get_role_user_user_id_role_get(user_id)

Get Role

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.role_schema import RoleSchema
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

# **get_stats_api_stats_get**
> DayStats get_stats_api_stats_get(telegram_id, x_telegram_init_data=x_telegram_init_data)

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
        api_response = api_instance.get_stats_api_stats_get(telegram_id, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->get_stats_api_stats_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_stats_api_stats_get: %s\n" % e)
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
**200** | Successful Response |  -  |
**204** | No Content |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_timezone_timezone_get**
> Dict[str, str] get_timezone_timezone_get(x_telegram_init_data=x_telegram_init_data)

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
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **patch_reminder_api_reminders_patch**
> Dict[str, object] patch_reminder_api_reminders_patch(reminder_schema, x_telegram_init_data=x_telegram_init_data)

Patch Reminder

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
        # Patch Reminder
        api_response = api_instance.patch_reminder_api_reminders_patch(reminder_schema, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->patch_reminder_api_reminders_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->patch_reminder_api_reminders_patch: %s\n" % e)
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

# **post_reminder_api_reminders_post**
> Dict[str, object] post_reminder_api_reminders_post(reminder_schema, x_telegram_init_data=x_telegram_init_data)

Post Reminder

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
        # Post Reminder
        api_response = api_instance.post_reminder_api_reminders_post(reminder_schema, x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->post_reminder_api_reminders_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->post_reminder_api_reminders_post: %s\n" % e)
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

# **profile_self_api_profile_self_get**
> UserContext profile_self_api_profile_self_get(x_telegram_init_data=x_telegram_init_data)

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
        api_response = api_instance.profile_self_api_profile_self_get(x_telegram_init_data=x_telegram_init_data)
        print("The response of DefaultApi->profile_self_api_profile_self_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->profile_self_api_profile_self_get: %s\n" % e)
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

# **put_role_user_user_id_role_put**
> RoleSchema put_role_user_user_id_role_put(user_id, role_schema)

Put Role

### Example


```python
import diabetes_sdk
from diabetes_sdk.models.role_schema import RoleSchema
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
> Dict[str, str] put_timezone_timezone_put(timezone, x_telegram_init_data=x_telegram_init_data)

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

**Dict[str, str]**

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

