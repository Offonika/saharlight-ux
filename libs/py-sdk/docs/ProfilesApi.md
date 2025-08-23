# diabetes_sdk.ProfilesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**profiles_get**](ProfilesApi.md#profiles_get) | **GET** /profiles | Profiles Get
[**profiles_post**](ProfilesApi.md#profiles_post) | **POST** /profiles | Profiles Post


# **profiles_get**
> ProfileSchema profiles_get(telegram_id=telegram_id, x_telegram_init_data=x_telegram_init_data)

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
    api_instance = diabetes_sdk.ProfilesApi(api_client)
    telegram_id = 56 # int |  (optional)
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Profiles Get
        api_response = api_instance.profiles_get(telegram_id=telegram_id, x_telegram_init_data=x_telegram_init_data)
        print("The response of ProfilesApi->profiles_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ProfilesApi->profiles_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telegram_id** | **int**|  | [optional] 
 **x_telegram_init_data** | **str**|  | [optional] 

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
**200** | Successful Response. Returns profile. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **profiles_post**
> ProfileSchema profiles_post(profile_schema, x_telegram_init_data=x_telegram_init_data)

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
    api_instance = diabetes_sdk.ProfilesApi(api_client)
    profile_schema = diabetes_sdk.ProfileSchema() # ProfileSchema | 
    x_telegram_init_data = 'x_telegram_init_data_example' # str |  (optional)

    try:
        # Profiles Post
        api_response = api_instance.profiles_post(profile_schema, x_telegram_init_data=x_telegram_init_data)
        print("The response of ProfilesApi->profiles_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ProfilesApi->profiles_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **profile_schema** | [**ProfileSchema**](ProfileSchema.md)|  | 
 **x_telegram_init_data** | **str**|  | [optional] 

### Return type

[**ProfileSchema**](ProfileSchema.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response. Returns profile. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

