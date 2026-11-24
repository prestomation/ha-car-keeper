# Odometer

Each car has 1 odometer, in the unit of the car: kilometres or miles. Every job with a
distance counts from it.

## Type a reading

Type the new reading in **Odometer** and select **Save**. Every Home Assistant user can do
this, on the page of the car or on the car card.

A reading cannot go down. A lower value shows an error, and the odometer keeps its value.
A service with a reading above the odometer also moves the odometer.

## Read a sensor

A car integration can report the odometer. In **Car details**, select **Edit**. Then set
**Odometer source** to **A sensor** and type the entity id of the sensor. Car Keeper
converts the unit of the sensor to the unit of the car.

A sensor that reports 1 lower value is noise, and Car Keeper ignores it. 2 lower values in
a row show a repair issue. Then check the sensor. If the car has a new instrument cluster,
an admin corrects the odometer with the service `car_keeper.correct_odometer`, which can
also set an offset.

## The odometer sensor

Each car has the entity **Odometer** with the reading. Home Keeper uses this entity for
each distance task, so a car with no car integration also has distance reminders.
