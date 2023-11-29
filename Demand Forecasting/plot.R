library(dplyr)
library(ggplot2)
library(readr)

data <- read_csv("forecast.csv")
data$block <- as.factor(data$block)

p <- ggplot(
  data = data |> subset(date >= "2023-10-15"),
  mapping = aes(x = when, shape = block)
) +
  geom_line(
    alpha = 0.5,
    color = "#32566a",
    mapping = aes(y = forecast)
  ) +
  geom_point(
    alpha = 0.75,
    color = "#32566a",
    mapping = aes(y = forecast)
  ) +
  geom_segment(
    alpha = 0.75,
    color = "orange",
    mapping = aes(
      xend = when,
      y = demand,
      yend = forecast
    )
  ) +
  geom_point(
    alpha = 0.75,
    color = "orange",
    mapping = aes(y = demand)
  ) +
  theme_light()

ggsave(
  filename = "demand-forecast.png",
  plot = p,
  width = 12,
  height = 8,
  units = "in"
)
