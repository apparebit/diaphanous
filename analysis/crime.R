library(tidyverse)

nibrs <- read.csv("data/nibrs/offenders.csv")
nibrs <- nibrs |>
  mutate(
    Group = factor(Group, levels = c("Child", "Adolescent", "Adult")),
    Sex = factor(Sex, levels = c("Female", "Male")),
    Race = factor(Race, levels = c("White", "Black", "Hispanic", "Other"))
  )


library(vcdExtra)

cat("\n================================================================================\n")
cat("US Crime Stats\n\n")

for (year in 2023:2024) {
  us.year <- nibrs |> filter(Year == year)
  cat("--------------------------------------------------------------------------------\n")
  cat(paste0("Age Group/Race/Sex ", year, "\n\n"))

  us.contab <- xtabs(Count ~ Group + Race + Sex, data = us.year)
  print(us.contab)

  svg(paste0("figure/us-age-race-sex-", year, ".svg"))
  vcd::mosaic(
    ~ Group + Race + Sex, data = nibrs.24.contab, direction = c("v", "h", "v"),
    shade = TRUE,
    main = paste0("Offenders by Age Group/Race/Sex (U.S., ", year, ")"),
    rot_labels = c(0, 0, 45, 0),
    offset_labels = c(0, 0, -0.5, -0.5),
    just_labels = c("center", "left", "right", "right"),
    offset_varnames = c(0.2, 0, 0.2, 0.2),
    margins = c(3, 0.3, 3, 4)
  )
  dev.off()

  cat("--------------------------------------------------------------------------------\n")
  cat(paste0("Age Group/Sex ", year, "\n\n"))

  us.contab <- xtabs(Count ~ Group + Sex, data = us.year)
  print(us.contab)

  svg(paste0("figure/us-age-sex-", year, ".svg"))
  vcd::mosaic(
    ~ Group + Sex,
    data = us.contab,
    direction = c("v", "h"),
    shade = TRUE,
    margins = c(2.5, 0.3, 0, 2.5),
    main = paste0("Offenders by Age Group/Sex (U.S., ", year, ")")
  )
  dev.off()
}

cat("\n================================================================================\n")
cat("German Crime Stats\n\n")

de <- read_csv("data/bka/suspects.csv") |>
  mutate(
    Group = factor(Group, levels = c("Child", "Adolescent", "Adult")),
    Sex = factor(Sex, levels = c("Female", "Male")),
  )

for (year in 2023:2024) {
  de.year <- de |> filter(Year == year)

  cat("--------------------------------------------------------------------------------\n")
  cat(paste0("Age Group/Sex ", year, "\n\n"))

  de.contab <- xtabs(Count ~ Group + Sex, data = de.year)
  print(de.contab)

  svg(paste0("figure/de-age-sex-", year, ".svg"))
  vcd::mosaic(
    ~ Group + Sex,
    data = de.contab,
    direction = c("v", "h"),
    shade = TRUE,
    margins = c(2.5, 0.3, 0, 2.5),
    main = paste0("Offenders by Age Group/Sex (Germany, ", year, ")")
  )
  dev.off()
}
