print(paste("Working directory : ", getwd()))

library(dplyr)
library(car)
library(ggplot2)
library(patchwork)
library(scales)
library(purrr)

# ----- The data -----
data.path <- normalizePath(file.path("data", "ocse-reports-per-year.csv"))
data <- read.csv(data.path) |> filter(year >= 2014) |> arrange(year)

print(data)

# ----- The models -----
data.em <- lm(log(reports) ~ year, data=data)
data.lm <- lm(reports ~ year, data=data)

print(summary(data.em))
print(summary(data.lm))

# ----- Linear Model Fit -----
print(outlierTest(data.lm))

par(mfrow = c(3, 2))
plot(data.lm, which = 1:6)

data <- data |> mutate(residuals = data.lm$residuals) |>
  mutate(predicted = predict(data.lm, select(data, year))) |>
  mutate(differences = reports - predicted)

# Check that R's residuals and manually computed residuals are consistent
stopifnot(all(abs(data$residuals - data$differences) < 0.00001))

# ----- Standard residuals -----
data <- data |> mutate(std_residuals = rstandard(data.lm))
data.sresid <- data |> select(year, std_residuals)
print(data.sresid)

write.csv(data.sresid, "data/ocse-reports-std-residuals.csv", row.names = FALSE)
