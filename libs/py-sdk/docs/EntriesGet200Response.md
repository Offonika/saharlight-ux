# EntriesGet200Response


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
from diabetes_sdk.models.entries_get200_response import EntriesGet200Response

# TODO update the JSON string below
json = "{}"
# create an instance of EntriesGet200Response from a JSON string
entries_get200_response_instance = EntriesGet200Response.from_json(json)
# print the JSON string representation of the object
print(EntriesGet200Response.to_json())

# convert the object into a dict
entries_get200_response_dict = entries_get200_response_instance.to_dict()
# create an instance of EntriesGet200Response from a dict
entries_get200_response_from_dict = EntriesGet200Response.from_dict(entries_get200_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


