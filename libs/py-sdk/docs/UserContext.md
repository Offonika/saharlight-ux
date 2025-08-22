# UserContext

Telegram user data supplied via WebApp init data.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **int** |  | 
**first_name** | **str** |  | [optional] 
**last_name** | **str** |  | [optional] 
**username** | **str** |  | [optional] 
**language_code** | **str** |  | [optional] 
**is_premium** | **bool** |  | [optional] 

## Example

```python
from diabetes_sdk.models.user_context import UserContext

# TODO update the JSON string below
json = "{}"
# create an instance of UserContext from a JSON string
user_context_instance = UserContext.from_json(json)
# print the JSON string representation of the object
print(UserContext.to_json())

# convert the object into a dict
user_context_dict = user_context_instance.to_dict()
# create an instance of UserContext from a dict
user_context_from_dict = UserContext.from_dict(user_context_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


