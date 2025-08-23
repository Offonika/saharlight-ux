# ResponseApiRemindersRemindersGet


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**telegram_id** | **int** |  | 
**id** | **int** |  | [optional] 
**type** | **str** |  | 
**time** | **str** |  | [optional] 
**interval_hours** | **int** |  | [optional] 
**minutes_after** | **int** |  | [optional] 
**is_enabled** | **bool** |  | [optional] [default to True]
**org_id** | **int** |  | [optional] 

## Example

```python
from diabetes_sdk.models.response_api_reminders_reminders_get import ResponseApiRemindersRemindersGet

# TODO update the JSON string below
json = "{}"
# create an instance of ResponseApiRemindersRemindersGet from a JSON string
response_api_reminders_reminders_get_instance = ResponseApiRemindersRemindersGet.from_json(json)
# print the JSON string representation of the object
print(ResponseApiRemindersRemindersGet.to_json())

# convert the object into a dict
response_api_reminders_reminders_get_dict = response_api_reminders_reminders_get_instance.to_dict()
# create an instance of ResponseApiRemindersRemindersGet from a dict
response_api_reminders_reminders_get_from_dict = ResponseApiRemindersRemindersGet.from_dict(response_api_reminders_reminders_get_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


