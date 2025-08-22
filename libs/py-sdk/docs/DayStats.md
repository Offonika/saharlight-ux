# DayStats


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**sugar** | **float** |  | 
**bread_units** | **float** |  | 
**insulin** | **float** |  | 

## Example

```python
from diabetes_sdk.models.day_stats import DayStats

# TODO update the JSON string below
json = "{}"
# create an instance of DayStats from a JSON string
day_stats_instance = DayStats.from_json(json)
# print the JSON string representation of the object
print(DayStats.to_json())

# convert the object into a dict
day_stats_dict = day_stats_instance.to_dict()
# create an instance of DayStats from a dict
day_stats_from_dict = DayStats.from_dict(day_stats_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


