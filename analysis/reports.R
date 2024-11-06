print(paste("Working directory : ", getwd()))

library(dplyr)
library(ggplot2)
library(patchwork)
library(scales)
library(purrr)

data <- read.csv(normalizePath(file.path("data", "ocse-reports-per-year.csv"))) |>
    filter(year >= 2014)
data.lm <- lm(reports~year, data=data)

summary(data.lm)

data <- data |> mutate(residuals=data.lm$residuals) |>
    mutate(predicted=predict(data.lm, select(data, year))) |>
    mutate(differences=reports - predicted)

stopifnot(all(abs(data$residuals - data$differences) < 0.000001))

data <- data |>
    mutate(std_residuals=rstandard(data.lm)) |>
    mutate(std_residuals_too=residuals/1813580)

print(min(data$std_residuals))
print(max(data$std_residuals))

print(data)

data.exp <- data |> select(year, std_residuals)
print(data.exp)

write.csv(data.exp,"data/ocse-reports-std-residuals.csv", row.names=FALSE)
