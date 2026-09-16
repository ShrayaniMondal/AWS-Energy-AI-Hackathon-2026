args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  stop("Usage: Rscript generate/plot_ggplot.R visualization_points.csv [output_dir]")
}

csv_path <- args[[1]]
output_dir <- ifelse(length(args) >= 2, args[[2]], "outputs/seismic_catalog/plots")
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

suppressPackageStartupMessages(library(ggplot2))

points <- read.csv(csv_path)

inline_plot <- ggplot(points, aes(x = inline_m, y = depth_m, color = amplitude)) +
  geom_point(size = 0.8, alpha = 0.75) +
  scale_y_reverse() +
  scale_color_gradient2(low = "#2166ac", mid = "white", high = "#b2182b") +
  labs(
    title = "Synthetic seismic section",
    x = "Inline (m)",
    y = "Depth (m)",
    color = "Amplitude"
  ) +
  theme_minimal()

reservoir_plot <- ggplot(points, aes(x = inline_m, y = crossline_m, color = reservoir_probability)) +
  geom_point(size = 0.8, alpha = 0.75) +
  scale_color_viridis_c() +
  labs(
    title = "Reservoir probability map",
    x = "Inline (m)",
    y = "Crossline (m)",
    color = "Reservoir"
  ) +
  theme_minimal()

ggsave(file.path(output_dir, "inline_depth_amplitude_ggplot.png"), inline_plot, width = 11, height = 6)
ggsave(file.path(output_dir, "reservoir_map_ggplot.png"), reservoir_plot, width = 9, height = 7)
