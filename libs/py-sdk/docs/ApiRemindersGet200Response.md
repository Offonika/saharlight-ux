# ApiRemindersGet200Response


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**telegram_id** | **int** |  | 
**id** | **int** |  | [optional] 
**type** | **str** |  | 
**time** | **str** |  | [optional] 
**interval_hours** | **int** |  | [optional] 
**is_enabled** | **bool** |  | [optional] 

## Example

```python
from diabetes_sdk.models.api_reminders_get200_response import ApiRemindersGet200Response

# TODO update the JSON string below
json = "{}"
# create an instance of ApiRemindersGet200Response from a JSON string
api_reminders_get200_response_instance = ApiRemindersGet200Response.from_json(json)
# print the JSON string representation of the object
print(ApiRemindersGet200Response.to_json())

# convert the object into a dict
api_reminders_get200_response_dict = api_reminders_get200_response_instance.to_dict()
# create an instance of ApiRemindersGet200Response from a dict
api_reminders_get200_response_from_dict = ApiRemindersGet200Response.from_dict(api_reminders_get200_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


