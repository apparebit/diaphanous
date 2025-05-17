.libPaths("/Volumes/rgrimmdatsa/Work/diaphanous/rlib")

library(dplyr)

library(ggplot2)
library(patchwork)
library(scales)
library(purrr)

data <- read.csv("../data/series.csv") |> filter(rank > 3)

mod_c2023 <- lm(c2023 ~ exp(rank), data = data)
mod_a2023 <- lm(a2023 ~ exp(rank), data = data)

ggplot(data = data) +
  geom_line(mapping = aes(x = rank, y = c2020), color = "#3178ea") +
  geom_line(mapping = aes(x = rank, y = a2020), color = "#d72827") +
  geom_line(mapping = aes(x = rank, y = c2021), color = "#3178eac0") +
  geom_line(mapping = aes(x = rank, y = a2021), color = "#d72827c0") +
  geom_line(mapping = aes(x = rank, y = c2022), color = "#3178ea80") +
  geom_line(mapping = aes(x = rank, y = a2022), color = "#d7282780") +
  geom_line(mapping = aes(x = rank, y = c2023), color = "#3178ea40") +
  geom_line(mapping = aes(x = rank, y = a2023), color = "#d7282740")
  
print(summary(mod))