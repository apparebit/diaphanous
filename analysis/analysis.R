library(tidyverse)
library(car)


yearly.reports <- (
  read.csv("data/ocse-reports-per-year.csv")
  |> left_join(read.csv("data/populations-simple.csv"), by = join_by(year))
  |> left_join(read.csv("data/internet-users-un.csv"), by = join_by(year))
  |> left_join(read.csv("data/social-accounts.csv"), by = join_by(year))
  |> mutate(
    internet_users = internet_users_pct * population / 100,
    social_accounts = million_accounts * 1000000,
  )
  |> select(year, reports, population, internet_users, social_accounts)
)

yearly.reports.mods <- list(
  lm.year = lm(reports ~ year, data = yearly.reports),
  lm.pop  = lm(reports ~ population, data = yearly.reports),
  lm.inet = lm(reports ~ internet_users, data = yearly.reports),
  lm.soc  = lm(reports ~ social_accounts, data = yearly.reports)
)

for (name in names(yearly.reports.mods)) {
  print("────────────────────────────────────────────────────────────────────────────────")
  mod <- yearly.reports.mods[[name]]
  print(summary(mod))
  print(qqPlot(mod, main = name))
}


# ======================================================================================

# for (name in names(yearly.reports.mods)) {
#   mod <- yearly.reports.mods[name]
#   qqPlot(mod)
# }
# qqPlot(yearly.lm)
# ggplot(data = yearly.reports, aes(x = yearly.lm$residuals)) +
#   geom_histogram(bins = 10, fill = "steelblue", color = "black")

# internet_users <- read.csv("data/internet-users-un.csv")
# social_accounts <- read.csv("data/social-accounts.csv")
# ggplot(reports_ncmec, aes(x = year, y = reports)) +
#   geom_line() + geom_point()
# hypergrowth = reports_ncmec |> filter(2014 <= year & year < 2024)
# ggplot(hypergrowth, aes(x = year, y = reports)) +
#   geom_line() + geom_point()

# rpy <- (
#   read.csv(paste(getwd(), "data/ocse-reports-per-year.csv", sep="/"))
#   |> filter(2014 <= year & year <= 2023)
#   |> rename(ds = year, y = reports)
#   |> mutate(ds = as.Date(ISOdate(ds, 12, 31)))
# )
#
# library(prophet)
# rpy.m <- prophet(rpy)
# rpy.future <- make_future_dataframe(rpy.m, periods = 10, freq = "year")
# rpy.forecast <- predict(rpy.m, rpy.future)
# plot(rpy.m, rpy.forecast)


if (FALSE) {
  #| code-summary: Load packages and data
  library(tidyverse)

  # Avoid scientific notation
  options(scipen=999)

  yearly.reports <- (
    read.csv("../data/ocse-reports-per-year.csv")
    |> left_join(read.csv("../data/populations-simple.csv"), by = join_by(year))
    |> left_join(read.csv("../data/internet-users-un.csv"), by = join_by(year))
    |> left_join(read.csv("../data/social-accounts.csv"), by = join_by(year))
    |> mutate(
      internet_users = internet_users_pct * population / 100,
      social_accounts = million_accounts * 1000000
    )
    |> select(year, reports, population, internet_users, social_accounts)
    |> filter(2014 <= year & year < 2023)
  )


  library(MASS)

  yearly.reports.mods <- list(
    lm.year = lm(reports ~ year, data = yearly.reports),
    lm.pop  = lm(reports ~ population, data = yearly.reports),
    lm.inet = lm(reports ~ internet_users, data = yearly.reports),
    lm.soc  = lm(reports ~ social_accounts, data = yearly.reports),
    poi.id.soc = glm(reports ~ social_accounts, data = yearly.reports, family = poisson(link = "identity")),
    poi.log.soc = glm(reports ~ social_accounts, data = yearly.reports, family = poisson(link = "log")),
    poi.sqrt.soc = glm(reports ~ social_accounts, data = yearly.reports, family = poisson(link = "sqrt")),
    nb.id.soc = glm.nb(reports ~ social_accounts, data = yearly.reports, link = identity),
    nb.log.soc = glm.nb(reports ~ social_accounts, data = yearly.reports, link = log),
    nb.sqrt.soc = glm.nb(reports ~ social_accounts, data = yearly.reports, link = sqrt)
  )

  show.model.fit <- function(name) {
    mod <- yearly.reports.mods[[name]]
    print(summary(mod))

    par(mfrow = c(2, 2))
    plot(mod)
    par(mfrow = c(1, 1))
  }

  show.model.fit("nb.sqrt.soc")


  #library(tidyverse)
  library(nanoparquet)

  offenders <- read_parquet("/Volumes/rgrimm/Work/diaphanous/data/nibrs/ingested/2023/offenders.parquet")

  age_sex_race <- (
    offenders
    |> mutate(
      age_group = cut(age_id, breaks = c(0, 17, 21, 103), labels = c("child", "adolescent", "adult"))
    ) |> select(
      age_group, sex_code, race_id
    ) |> ftable(row.vars = 1:3)
  )

  print(age_sex_race)

}
