# HistoryRecordSchemaInput

Schema for user history records.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**var_date** | **date** |  | 
**time** | **str** |  | 
**sugar** | **float** |  | [optional] 
**carbs** | **float** |  | [optional] 
**bread_units** | **float** |  | [optional] 
**insulin** | **float** |  | [optional] 
**notes** | **str** |  | [optional] 
**type** | **str** |  | 

## Example

```python
from diabetes_sdk.models.history_record_schema_input import HistoryRecordSchemaInput

# TODO update the JSON string below
json = "{}"
# create an instance of HistoryRecordSchemaInput from a JSON string
history_record_schema_input_instance = HistoryRecordSchemaInput.from_json(json)
# print the JSON string representation of the object
print(HistoryRecordSchemaInput.to_json())

# convert the object into a dict
history_record_schema_input_dict = history_record_schema_input_instance.to_dict()
# create an instance of HistoryRecordSchemaInput from a dict
history_record_schema_input_from_dict = HistoryRecordSchemaInput.from_dict(history_record_schema_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


