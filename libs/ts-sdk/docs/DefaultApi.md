# DefaultApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiRemindersGet**](#apiremindersget) | **GET** /api/reminders | List or retrieve reminders|
|[**apiRemindersPost**](#apireminderspost) | **POST** /api/reminders | Save reminder|
|[**healthGet**](#healthget) | **GET** /health | Health check|
|[**profilesGet**](#profilesget) | **GET** /profiles | Get user profile|
|[**profilesPost**](#profilespost) | **POST** /profiles | Save user profile|
|[**timezonePost**](#timezonepost) | **POST** /timezone | Save timezone|

# **apiRemindersGet**
> ApiRemindersGet200Response apiRemindersGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let telegramId: number; // (default to undefined)
let id: number; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiRemindersGet(
    telegramId,
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **telegramId** | [**number**] |  | defaults to undefined|
| **id** | [**number**] |  | (optional) defaults to undefined|


### Return type

**ApiRemindersGet200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiRemindersPost**
> ApiRemindersPost200Response apiRemindersPost(reminder)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    Reminder
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let reminder: Reminder; //

const { status, data } = await apiInstance.apiRemindersPost(
    reminder
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **reminder** | **Reminder**|  | |


### Return type

**ApiRemindersPost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **healthGet**
> Status healthGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.healthGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**Status**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **profilesGet**
> Profile profilesGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let telegramId: number; // (default to undefined)

const { status, data } = await apiInstance.profilesGet(
    telegramId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **telegramId** | [**number**] |  | defaults to undefined|


### Return type

**Profile**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **profilesPost**
> Status profilesPost(profile)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    Profile
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let profile: Profile; //

const { status, data } = await apiInstance.profilesPost(
    profile
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **profile** | **Profile**|  | |


### Return type

**Status**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **timezonePost**
> Status timezonePost(timezone)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    Timezone
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let timezone: Timezone; //

const { status, data } = await apiInstance.timezonePost(
    timezone
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **timezone** | **Timezone**|  | |


### Return type

**Status**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

