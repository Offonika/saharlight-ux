# ReminderSchema


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**telegram_id** | **int** |  | 
**id** | **int** |  | [optional] 
**type** | **str** |  | 
**title** | **str** |  | [optional] 
**time** | **str** |  | [optional] 
**interval_hours** | **int** |  | [optional] 
**minutes_after** | **int** |  | [optional] 
**is_enabled** | **bool** |  | [optional] [default to True]
**org_id** | **int** |  | [optional] 

## Example

```python
from diabetes_sdk.models.reminder_schema import ReminderSchema

# TODO update the JSON string below
json = "{}"
# create an instance of ReminderSchema from a JSON string
reminder_schema_instance = ReminderSchema.from_json(json)
# print the JSON string representation of the object
print(ReminderSchema.to_json())

# convert the object into a dict
reminder_schema_dict = reminder_schema_instance.to_dict()
# create an instance of ReminderSchema from a dict
reminder_schema_from_dict = ReminderSchema.from_dict(reminder_schema_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


