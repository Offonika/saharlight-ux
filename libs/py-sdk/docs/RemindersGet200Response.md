# RemindersGet200Response


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**telegram_id** | **int** |  | 
**id** | **int** |  | [optional] 
**type** | **str** |  | 
**time** | **str** |  | [optional] 
**interval_hours** | **int** |  | [optional] 
**minutes_after** | **int** |  | [optional] 
**is_enabled** | **bool** |  | [optional] 

## Example

```python
from diabetes_sdk.models.reminders_get200_response import RemindersGet200Response

# TODO update the JSON string below
json = "{}"
# create an instance of RemindersGet200Response from a JSON string
reminders_get200_response_instance = RemindersGet200Response.from_json(json)
# print the JSON string representation of the object
print(RemindersGet200Response.to_json())

# convert the object into a dict
reminders_get200_response_dict = reminders_get200_response_instance.to_dict()
# create an instance of RemindersGet200Response from a dict
reminders_get200_response_from_dict = RemindersGet200Response.from_dict(reminders_get200_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


