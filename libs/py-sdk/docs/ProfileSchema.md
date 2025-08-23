# ProfileSchema


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**telegram_id** | **int** |  | 
**icr** | **float** |  | 
**cf** | **float** |  | 
**target** | **float** |  | 
**low** | **float** |  | 
**high** | **float** |  | 
**sos_contact** | **str** |  | [optional] 
**sos_alerts_enabled** | **bool** |  | [optional] [default to True]
**org_id** | **int** |  | [optional] 

## Example

```python
from diabetes_sdk.models.profile_schema import ProfileSchema

# TODO update the JSON string below
json = "{}"
# create an instance of ProfileSchema from a JSON string
profile_schema_instance = ProfileSchema.from_json(json)
# print the JSON string representation of the object
print(ProfileSchema.to_json())

# convert the object into a dict
profile_schema_dict = profile_schema_instance.to_dict()
# create an instance of ProfileSchema from a dict
profile_schema_from_dict = ProfileSchema.from_dict(profile_schema_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


