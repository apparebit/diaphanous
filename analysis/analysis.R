library(dplyr)

rpy <- (
  read.csv(paste(getwd(), "data/ocse-reports-per-year.csv", sep="/"))
  |> filter(2014 <= year & year <= 2023)
  |> rename(ds = year, y = reports)
  |> mutate(ds = as.Date(ISOdate(ds, 12, 31)))
)

library(prophet)
rpy.m <- prophet(rpy)
rpy.future <- make_future_dataframe(rpy.m, periods = 10, freq = "year")
rpy.forecast <- predict(rpy.m, rpy.future)
plot(rpy.m, rpy.forecast)
