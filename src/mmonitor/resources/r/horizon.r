library(latticeExtra)

abundances <- read.csv(file = Sys.getenv("HORI_CSV"))
width <- strtoi(Sys.getenv("HORI_WIDTH"))
height <- strtoi(Sys.getenv("HORI_HEIGHT"))

png(Sys.getenv("HORI_IMAGE"), width = width, height = height)

horizonplot(ts(abundances), colorkey = TRUE, layout = c(1, ncol(abundances)))

dev.off()
