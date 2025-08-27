# ReminderSchema


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**telegram_id** | **int** |  | 
**id** | **int** |  | [optional] 
**type** | [**ReminderType**](ReminderType.md) |  | 
**title** | **str** |  | [optional] 
**kind** | [**ScheduleKind**](ScheduleKind.md) |  | [optional] 
**time** | **str** |  | [optional] 
**interval_minutes** | **int** |  | [optional] 
**minutes_after** | **int** |  | [optional] 
**interval_hours** | **int** |  | [optional] 
**days_of_week** | **List[int]** |  | [optional] 
**is_enabled** | **bool** |  | [optional] [default to True]
**org_id** | **int** |  | [optional] 
**last_fired_at** | **datetime** |  | [optional] 

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


