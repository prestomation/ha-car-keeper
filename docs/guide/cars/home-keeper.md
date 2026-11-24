# Home Keeper tasks and parts

Car Keeper does not send its own reminders. Home Keeper does: the to-do list, the
calendar and the notifications.

## Appliances and tasks

Each car is an appliance in Home Keeper. Each job with **Make a Home Keeper task** is a
task on that appliance.

| Job | Home Keeper task |
|---|---|
| With a distance | A usage task on the odometer sensor of the car. A time interval is its backstop. |
| With a time only | A task that repeats after the interval. |
| A date job | A task with the due date. |

The appliance has the name and the area of the car, with its make and model. It never has
the VIN or the plate.

## Both ways

A service in Car Keeper marks the task done in Home Keeper. A task done in Home Keeper
logs a service in Car Keeper, with its date and reading. An undo in Home Keeper takes the
job off its service.

If you delete the task in Home Keeper, the job stays in Car Keeper with no task.

## Parts and stock

Add the parts of a car to its appliance in Home Keeper, such as an oil filter. Then link
a part to a job with the `parts` field of `car_keeper.update_item`. Home Keeper takes the
part off the stock when the job is done.

A service can also use more parts. The `parts_used` field of `car_keeper.log_service`
takes them off the stock.

## Remove Car Keeper

When you remove Car Keeper, the appliances stay in Home Keeper with their parts and
stock.
