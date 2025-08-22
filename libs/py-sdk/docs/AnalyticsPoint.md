# AnalyticsPoint


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**var_date** | **str** |  | 
**sugar** | **float** |  | 

## Example

```python
from diabetes_sdk.models.analytics_point import AnalyticsPoint

# TODO update the JSON string below
json = "{}"
# create an instance of AnalyticsPoint from a JSON string
analytics_point_instance = AnalyticsPoint.from_json(json)
# print the JSON string representation of the object
print(AnalyticsPoint.to_json())

# convert the object into a dict
analytics_point_dict = analytics_point_instance.to_dict()
# create an instance of AnalyticsPoint from a dict
analytics_point_from_dict = AnalyticsPoint.from_dict(analytics_point_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


