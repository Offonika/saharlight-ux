# DefaultApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**authPost**](#authpost) | **POST** /auth | Authenticate user|
|[**entriesGet**](#entriesget) | **GET** /entries | List or retrieve entries|
|[**entriesPost**](#entriespost) | **POST** /entries | Save entry|
|[**profilesGet**](#profilesget) | **GET** /profiles | Get user profile|
|[**profilesPost**](#profilespost) | **POST** /profiles | Save user profile|
|[**remindersGet**](#remindersget) | **GET** /reminders | List or retrieve reminders|
|[**remindersPost**](#reminderspost) | **POST** /reminders | Save reminder|
|[**reportsGet**](#reportsget) | **GET** /reports | Generate report|

# **authPost**
> AuthResponse authPost(authRequest)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    AuthRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let authRequest: AuthRequest; //

const { status, data } = await apiInstance.authPost(
    authRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **authRequest** | **AuthRequest**|  | |


### Return type

**AuthResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Authenticated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **entriesGet**
> EntriesGet200Response entriesGet()


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

const { status, data } = await apiInstance.entriesGet(
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

**EntriesGet200Response**

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

# **entriesPost**
> EntriesPost200Response entriesPost(entry)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    Entry
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let entry: Entry; //

const { status, data } = await apiInstance.entriesPost(
    entry
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **entry** | **Entry**|  | |


### Return type

**EntriesPost200Response**

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

# **remindersGet**
> RemindersGet200Response remindersGet()


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

const { status, data } = await apiInstance.remindersGet(
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

**RemindersGet200Response**

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

# **remindersPost**
> EntriesPost200Response remindersPost(reminder)


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

const { status, data } = await apiInstance.remindersPost(
    reminder
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **reminder** | **Reminder**|  | |


### Return type

**EntriesPost200Response**

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

# **reportsGet**
> File reportsGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let telegramId: number; // (default to undefined)
let periodDays: number; // (optional) (default to undefined)

const { status, data } = await apiInstance.reportsGet(
    telegramId,
    periodDays
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **telegramId** | [**number**] |  | defaults to undefined|
| **periodDays** | [**number**] |  | (optional) defaults to undefined|


### Return type

**File**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/pdf


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | PDF report |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

