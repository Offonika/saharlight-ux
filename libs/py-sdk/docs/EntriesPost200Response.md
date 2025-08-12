# EntriesPost200Response


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | **str** |  | [optional] 
**id** | **int** |  | [optional] 

## Example

```python
from diabetes_sdk.models.entries_post200_response import EntriesPost200Response

# TODO update the JSON string below
json = "{}"
# create an instance of EntriesPost200Response from a JSON string
entries_post200_response_instance = EntriesPost200Response.from_json(json)
# print the JSON string representation of the object
print(EntriesPost200Response.to_json())

# convert the object into a dict
entries_post200_response_dict = entries_post200_response_instance.to_dict()
# create an instance of EntriesPost200Response from a dict
entries_post200_response_from_dict = EntriesPost200Response.from_dict(entries_post200_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


