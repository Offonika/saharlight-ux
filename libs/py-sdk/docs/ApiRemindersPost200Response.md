# ApiRemindersPost200Response


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | **str** |  | [optional] 
**id** | **int** |  | [optional] 

## Example

```python
from diabetes_sdk.models.api_reminders_post200_response import ApiRemindersPost200Response

# TODO update the JSON string below
json = "{}"
# create an instance of ApiRemindersPost200Response from a JSON string
api_reminders_post200_response_instance = ApiRemindersPost200Response.from_json(json)
# print the JSON string representation of the object
print(ApiRemindersPost200Response.to_json())

# convert the object into a dict
api_reminders_post200_response_dict = api_reminders_post200_response_instance.to_dict()
# create an instance of ApiRemindersPost200Response from a dict
api_reminders_post200_response_from_dict = ApiRemindersPost200Response.from_dict(api_reminders_post200_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


