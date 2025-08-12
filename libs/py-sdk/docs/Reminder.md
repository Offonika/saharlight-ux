# Reminder


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
from diabetes_sdk.models.reminder import Reminder

# TODO update the JSON string below
json = "{}"
# create an instance of Reminder from a JSON string
reminder_instance = Reminder.from_json(json)
# print the JSON string representation of the object
print(Reminder.to_json())

# convert the object into a dict
reminder_dict = reminder_instance.to_dict()
# create an instance of Reminder from a dict
reminder_from_dict = Reminder.from_dict(reminder_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


