# diabetes_sdk.HistoryApi

All URIs are relative to */api*

Method | HTTP request | Description
------------- | ------------- | -------------
[**history_get**](HistoryApi.md#history_get) | **GET** /history | Get History
[**history_id_delete**](HistoryApi.md#history_id_delete) | **DELETE** /history/{id} | Delete History
[**history_post**](HistoryApi.md#history_post) | **POST** /history | Post History


# **history_get**
> List[HistoryRecordSchemaOutput] history_get()

Get History

Return history records for the authenticated user.

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.history_record_schema_output import HistoryRecordSchemaOutput
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
    api_instance = diabetes_sdk.HistoryApi(api_client)

    try:
        # Get History
        api_response = api_instance.history_get()
        print("The response of HistoryApi->history_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling HistoryApi->history_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**List[HistoryRecordSchemaOutput]**](HistoryRecordSchemaOutput.md)

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

# **history_id_delete**
> Dict[str, str] history_id_delete(id)

Delete History

Delete a history record after verifying ownership.

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
    api_instance = diabetes_sdk.HistoryApi(api_client)
    id = 'id_example' # str | 

    try:
        # Delete History
        api_response = api_instance.history_id_delete(id)
        print("The response of HistoryApi->history_id_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling HistoryApi->history_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **str**|  | 

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

# **history_post**
> Dict[str, str] history_post(history_record_schema_input)

Post History

Save or update a history record in the database.

### Example

* Api Key Authentication (telegramInitData):

```python
import diabetes_sdk
from diabetes_sdk.models.history_record_schema_input import HistoryRecordSchemaInput
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
    api_instance = diabetes_sdk.HistoryApi(api_client)
    history_record_schema_input = diabetes_sdk.HistoryRecordSchemaInput() # HistoryRecordSchemaInput | 

    try:
        # Post History
        api_response = api_instance.history_post(history_record_schema_input)
        print("The response of HistoryApi->history_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling HistoryApi->history_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **history_record_schema_input** | [**HistoryRecordSchemaInput**](HistoryRecordSchemaInput.md)|  | 

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

