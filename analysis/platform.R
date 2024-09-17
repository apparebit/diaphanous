# ======================================================================================
# Helper functions and Setup

root_path <- function() {
  cwd <- dirname(sys.frame(1)$ofile)
  return(normalizePath(file.path(cwd, "..")))
}

.libPaths(file.path(root_path(), "rlib"))

library(iccCounts)
library(dplyr)
library(ggplot2)
library(patchwork)
library(scales)
library(purrr)

data_path <- function(csv_name) {
  file.path(root_path(), "data", sprintf("%s.csv", csv_name))
}

format_mean_zero <- number_format()
format_mean_kilo <- number_format(scale=0.001, suffix="k")
format_mean_mega <- number_format(scale=0.000001, suffix="M")
format_mean <- function(x) {
  dplyr::case_when(
    is.na(x) ~ "",
    x == 0 ~ format_mean_zero(x),
    x < 1000000 ~ format_mean_kilo(x),
    TRUE ~ format_mean_mega(x)
  )
}

format_all_means <- function(xs) map(xs, format_mean)

# ======================================================================================
# Bland-Altman with percent differences

plot_percent_diff_over_mean <- function(data, title) {
  data <- data |>
    group_by(id) |>
    summarize(Mean = mean(count), Diff = combn(count, diff, m=2)) |>
    mutate(PctDiff = Diff / Mean * 100)

  ymax <- max(abs(data$PctDiff))
  ymean <- mean(data$PctDiff)
  xmax <- max(data$Mean)
  xmin <- min(data$Mean)
  xrange <- xmax - xmin

  graph <- ggplot(data = data, aes(x=Mean,y=(PctDiff))) +
    geom_point(size=2) +
    xlim(xmin - 0.05 * xrange, xmax + 0.05 * xrange) +
    ylim(ymax * (-1), ymax) +
    geom_hline(yintercept = 0) +
    geom_hline(yintercept = ymean, linetype = "dashed") +
    xlab("Mean") +
    ylab("Δ% (Mean)") +
    labs(title = title)

  graph$scales$scales[[1]]$labels <- format_all_means
  graph$scales$scales[[2]]$labels <- comma_format()

  graph <- graph + theme_light() #linedraw()

  return(graph)
}

# ======================================================================================
# Create individual and full Bland-Altman plots

per_provider_data <- read.csv(data_path("comparable-reports-by-provider"))
providers <- unique(per_provider_data$topic)
ba_plots <- vector("list", length(providers) + 1)

index <- 0
for (provider in providers) {
  index <- index + 1

  print("----------------------------------------------------------------------------")
  print(sprintf("Processing %s", provider))
  provider.data <- per_provider_data |>
    filter(topic == provider) |>
    rename(id = year)
  ba_plots[[index]] <- plot_percent_diff_over_mean(provider.data, provider)

  if (FALSE) {
    print("Beware: Negative binomial with quadratic variance is not a complete fit!")
    icc_data <- icc_counts(
      provider.data,
      y="count",
      id="id",
      met="observer",
      type="con",
      fam="nbinom2"
    )
    print(ICC(icc_data))
    print(VarComp(icc_data))
  }
}

print("----------------------------------------------------------------------------")
print("Processing All Providers")

all_data <- read.csv(data_path("comparable-reports"))
ba_plots[[length(providers) + 1]] <- plot_percent_diff_over_mean(
  all_data,
  "All Providers"
)

# Combine plots into 3x3 grid and display grid
grid <- wrap_plots(ba_plots, ncol=3)
print(grid)
ggsave(
  file.path(root_path(), "figure", "comparable-reports.svg"),
  grid,
  width=7,
  height=7
)

# ======================================================================================
# Compute Goodness-of-Fit for all reports

if (FALSE) {
  all_data.icc <- icc_counts(
    all_data,
    y="count",
    id="id",
    met="observer",
    type="con",
    fam="nbinom2"
  )
  print(ICC(all_data.icc))
  print(VarComp(all_data.icc))

  all_data.gof <- GOF_check(all_data.icc)
  print(DispersionTest(all_data.gof))

  plot(all_data.gof$plot_env + geom_point(size=2) + theme_linedraw())
}

# ======================================================================================
# Categorize differences and perform Fisher's exact test

if (FALSE) {
  cont <- read.csv(data_path("comparable-reports-contingencies"))
  cont <- select(cont, much_less:much_more)
  print(fisher.test(as.matrix(cont)))
}
