library(dplyr)
library(purrr)

data <- read.csv("../data/social-accounts-per-country.csv") |>
    filter(year > 2019) |>
    arrange(year)

data.summary <- data |>
    group_by(year) |>
    summarize(
        min = min(accounts_per_capita, na.rm = TRUE),
        q1 = quantile(accounts_per_capita, na.rm = TRUE, probs = c(0.25)),
        q2 = quantile(accounts_per_capita, na.rm = TRUE, probs = c(0.5)),
        q3 = quantile(accounts_per_capita, na.rm = TRUE, probs = c(0.75)),
        mean = mean(accounts_per_capita, na.rm = TRUE),
        sd = sd(accounts_per_capita, na.rm = TRUE),
        max = max(accounts_per_capita, na.rm = TRUE),
    )

print(data.summary)

bottom <- data |>
    filter(accounts_per_capita < 0.3) |>
    summarize(country = unique(country)) |>
    arrange()

print(bottom)
