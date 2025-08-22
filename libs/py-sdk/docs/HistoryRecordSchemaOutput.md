# HistoryRecordSchemaOutput

Schema for user history records.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**var_date** | **str** |  | 
**time** | **str** |  | 
**sugar** | **float** |  | [optional] 
**carbs** | **float** |  | [optional] 
**bread_units** | **float** |  | [optional] 
**insulin** | **float** |  | [optional] 
**notes** | **str** |  | [optional] 
**type** | **str** |  | 

## Example

```python
from diabetes_sdk.models.history_record_schema_output import HistoryRecordSchemaOutput

# TODO update the JSON string below
json = "{}"
# create an instance of HistoryRecordSchemaOutput from a JSON string
history_record_schema_output_instance = HistoryRecordSchemaOutput.from_json(json)
# print the JSON string representation of the object
print(HistoryRecordSchemaOutput.to_json())

# convert the object into a dict
history_record_schema_output_dict = history_record_schema_output_instance.to_dict()
# create an instance of HistoryRecordSchemaOutput from a dict
history_record_schema_output_from_dict = HistoryRecordSchemaOutput.from_dict(history_record_schema_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


