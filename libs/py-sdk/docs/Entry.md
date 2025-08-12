# Entry


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**telegram_id** | **int** |  | 
**id** | **int** |  | [optional] 
**event_time** | **datetime** |  | 
**photo_path** | **str** |  | [optional] 
**carbs_g** | **float** |  | [optional] 
**xe** | **float** |  | [optional] 
**sugar_before** | **float** |  | [optional] 
**dose** | **float** |  | [optional] 
**gpt_summary** | **str** |  | [optional] 

## Example

```python
from diabetes_sdk.models.entry import Entry

# TODO update the JSON string below
json = "{}"
# create an instance of Entry from a JSON string
entry_instance = Entry.from_json(json)
# print the JSON string representation of the object
print(Entry.to_json())

# convert the object into a dict
entry_dict = entry_instance.to_dict()
# create an instance of Entry from a dict
entry_from_dict = Entry.from_dict(entry_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


